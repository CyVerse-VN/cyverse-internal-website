import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable

import httpx

from app.tools.threads.ai import GroqThreadsAI, ThreadsAI
from app.tools.threads.config import ThreadsConfig
from app.tools.threads.crawler import ThreadsCrawler, open_crawler
from app.tools.threads.errors import ThreadsCancelled, ThreadsError
from app.tools.threads.schemas import ThreadsPost, ThreadsRequest, ThreadsResult

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float], Awaitable[None]]
CancellationCallback = Callable[[], Awaitable[bool]]
SnapshotCallback = Callable[[ThreadsResult], Awaitable[None]]


class ThreadsPipeline:
    def __init__(self, config: ThreadsConfig) -> None:
        self.config = config

    async def run(
        self,
        request: ThreadsRequest,
        on_progress: ProgressCallback,
        is_cancelled: CancellationCallback,
        *,
        crawler: ThreadsCrawler | None = None,
        ai: ThreadsAI | None = None,
        on_snapshot: SnapshotCallback | None = None,
        existing_post_ids: set[str] | None = None,
    ) -> ThreadsResult:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            provider = ai or GroqThreadsAI(self.config, client)
            if crawler is not None:
                return await self._execute(
                    request, crawler, provider, on_progress, is_cancelled, on_snapshot, existing_post_ids
                )
            async with open_crawler(
                self.config,
                max_accounts=request.max_accounts,
                use_proxy=request.use_proxy,
                search_timeout_seconds=request.search_timeout_seconds,
            ) as browser:
                return await self._execute(
                    request, browser, provider, on_progress, is_cancelled, on_snapshot, existing_post_ids
                )

    async def _execute(
        self,
        request: ThreadsRequest,
        crawler: ThreadsCrawler,
        ai: ThreadsAI,
        on_progress: ProgressCallback,
        is_cancelled: CancellationCallback,
        on_snapshot: SnapshotCallback | None,
        existing_post_ids: set[str] | None = None,
    ) -> ThreadsResult:
        started = time.monotonic()
        warnings: list[str] = []
        logger.info(
            "Starting Threads pipeline (query: %r, expand_query: %s, pre_filter: %s, comments: %s, curate: %s)",
            request.query,
            request.expand_query,
            request.pre_filter,
            request.include_comments,
            request.curate,
        )

        async def checkpoint(stage: str, progress: float) -> None:
            if await is_cancelled():
                raise ThreadsCancelled()
            await on_progress(stage, progress)

        async def pause() -> None:
            await asyncio.sleep(
                random.uniform(request.min_delay_seconds, request.max_delay_seconds)
            )

        await checkpoint("planning", 0.05)
        keywords = request.keywords.copy()
        if not keywords and request.expand_query:
            try:
                keywords = await ai.keywords(request.query, count=request.keywords_per_query)
            except TypeError:
                keywords = await ai.keywords(request.query)
        if not keywords:
            if len(request.query) > 100:
                raise ThreadsError(
                    "KEYWORDS_REQUIRED", "Supply short keywords or enable query expansion."
                )
            keywords = [request.query]
        logger.info("Pipeline planning completed with %d keywords: %s", len(keywords), keywords)

        posts: dict[str, ThreadsPost] = {}
        urls: dict[str, str] = {}
        filtering = request.pre_filter and request.pre_filter_strictness != "none"
        curated: list[str] = []
        existing_ids = existing_post_ids or set()
        duplicate_count = 0

        def snapshot(selected_posts: list[ThreadsPost]) -> ThreadsResult:
            return ThreadsResult(
                query=request.query,
                keywords=keywords,
                posts=selected_posts,
                curated_post_ids=curated.copy(),
                total_comments=sum(len(post.comments) for post in selected_posts),
                duplicate_count=duplicate_count,
                duration_seconds=round(time.monotonic() - started, 2),
                warnings=warnings.copy(),
            )

        async def persist(selected_posts: list[ThreadsPost]) -> None:
            if await is_cancelled():
                raise ThreadsCancelled()
            if on_snapshot is not None:
                await on_snapshot(snapshot(selected_posts))

        search_types = (
            ["top", "recent"] if request.search_type == "both" else [request.search_type]
        )
        for index, keyword in enumerate(keywords):
            await checkpoint("searching", 0.1 + 0.3 * index / len(keywords))
            logger.info(
                "Searching keyword %d/%d: %r (search_modes: %s)",
                index + 1,
                len(keywords),
                keyword,
                search_types,
            )

            def capture_warning(
                message: str, number: int = index + 1, kw: str = keyword
            ) -> None:
                warn_msg = f"Keyword {number}: {message}"
                warnings.append(warn_msg)
                logger.warning("Search warning for keyword %r: %s", kw, message)

            for s_type in search_types:
                try:
                    batch = await crawler.search(
                        keyword,
                        request.max_posts_per_keyword,
                        s_type,
                        on_warning=capture_warning,
                    )
                except ThreadsCancelled:
                    raise
                except Exception as exc:
                    warn_msg = f"Keyword {index + 1} ({keyword}) in mode '{s_type}' search failed: {exc}"
                    warnings.append(warn_msg)
                    logger.warning(warn_msg, exc_info=True)
                    batch = []
                for post in batch:
                    if request.check_duplicate and post.post_id in existing_ids:
                        duplicate_count += 1
                        continue
                    key = post.post_id if post.post_id in posts else urls.get(post.url, post.post_id)
                    if key in posts:
                        duplicate_count += 1
                        posts[key].search_keywords = list(
                            dict.fromkeys([*posts[key].search_keywords, keyword])
                        )
                    else:
                        post.search_keywords = [keyword]
                        posts[key] = post
                        urls[post.url] = key
                if len(search_types) > 1:
                    await pause()
            # Persist intermediate snapshot to database after every keyword finishes
            await persist(list(posts.values()))
            await pause()
        all_posts = list(posts.values())
        logger.info(
            "Completed search across %d keywords: collected %d unique posts",
            len(keywords),
            len(all_posts),
        )
        if not all_posts:
            logger.warning(
                "No posts were found for query %r across keywords %s",
                request.query,
                keywords,
            )
            warnings.append(
                "No posts were found; check the query and account session if this persists."
            )
        candidates = all_posts
        if filtering:
            await checkpoint("filtering", 0.45)
            logger.info(
                "Starting AI relevance filtering on %d posts (strictness: %s)",
                len(all_posts),
                request.pre_filter_strictness,
            )
            selected: set[str] = set()
            for index in range(0, len(all_posts), 15):
                await checkpoint("filtering", 0.45)
                batch = all_posts[index : index + 15]
                try:
                    try:
                        batch_selected = await ai.filter(
                            request.query, batch, strictness=request.pre_filter_strictness
                        )
                    except TypeError:
                        batch_selected = await ai.filter(request.query, batch)
                except Exception as exc:
                    logger.error(
                        "AI filtering failed on batch [%d:%d] (%d posts): %s (%s)",
                        index,
                        index + len(batch),
                        len(batch),
                        type(exc).__name__,
                        exc,
                    )
                    raise
                selected.update(batch_selected)
                # Rejected posts never enter PostgreSQL when relevance filtering is enabled.
                await persist([post for post in all_posts if post.post_id in selected])
                await pause()
            candidates = [post for post in all_posts if post.post_id in selected]
            logger.info(
                "AI relevance filtering finished: kept %d of %d posts",
                len(candidates),
                len(all_posts),
            )

        await persist(candidates)

        if request.include_comments:
            filtered_candidates = (
                candidates
                if request.min_replies <= 0
                else [post for post in candidates if post.reply_count >= request.min_replies]
            )
            targets = sorted(
                filtered_candidates,
                key=lambda post: post.reply_count,
                reverse=True,
            )
            if request.max_comment_posts > 0:
                targets = targets[: request.max_comment_posts]
            logger.info(
                "Starting comment collection for %d posts (max comments per post: %d)",
                len(targets),
                request.max_comments_per_post,
            )
            for index, post in enumerate(targets):
                await checkpoint("comments", 0.5 + 0.2 * index / max(len(targets), 1))
                try:
                    post.comments = await crawler.comments(post.url, request.max_comments_per_post)
                except Exception as exc:
                    logger.error(
                        "Failed to fetch comments for post %s (%s): %s (%s)",
                        post.post_id,
                        post.url,
                        type(exc).__name__,
                        exc,
                    )
                    raise
                await persist(candidates)
                await pause()

        if request.curate:
            logger.info("Starting AI curation for %d posts", len(candidates))
            for index, post in enumerate(candidates):
                await checkpoint("curating", 0.75 + 0.2 * index / len(candidates))
                try:
                    post.ai_analysis = await ai.curate(request.query, post)
                except Exception as exc:
                    logger.error(
                        "Failed AI curation for post %s (%s): %s (%s)",
                        post.post_id,
                        post.url,
                        type(exc).__name__,
                        exc,
                    )
                    raise
                if post.ai_analysis.is_relevant:
                    curated.append(post.post_id)
                await persist(candidates)
            logger.info("AI curation completed: %d curated relevant posts", len(curated))
        await checkpoint("saving", 0.98)
        result = snapshot(candidates)
        logger.info(
            "Pipeline completed in %.2fs: %d posts, %d comments, %d curated, %d warnings",
            result.duration_seconds,
            len(result.posts),
            result.total_comments,
            len(result.curated_post_ids),
            len(result.warnings),
        )
        return result
