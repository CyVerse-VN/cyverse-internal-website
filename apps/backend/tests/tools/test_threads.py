import asyncio
import json
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.models.threads import ThreadsCommentRecord, ThreadsPostRecord, ThreadsResultRecord
from app.models.tool_run import ToolRun
from app.models.user import User
from app.tools.threads.ai import GroqThreadsAI
from app.tools.threads.artifacts import ThreadsArtifacts
from app.tools.threads.auth import save_session, submit_credentials
from app.tools.threads.cloudinary import (
    CloudinaryConfig,
    CloudinaryTextStore,
    archive_public_id,
)
from app.tools.threads.config import ThreadsAccount, ThreadsConfig
from app.tools.threads.content import clean_stored_comment, dom_comment_text
from app.tools.threads.crawler import (
    PlaywrightThreadsCrawler,
    allowed_browser_url,
    open_crawler,
    playwright_proxy,
)
from app.tools.threads.errors import ThreadsCancelled, ThreadsError
from app.tools.threads.parser import extract_comments, extract_search_posts, search_has_next_page
from app.tools.threads.pipeline import ThreadsPipeline
from app.tools.threads.repository import ThreadsRepository, to_response
from app.tools.threads.schemas import (
    ThreadsAnalysis,
    ThreadsComment,
    ThreadsPost,
    ThreadsRequest,
    ThreadsResult,
)
from app.tools.threads.service import ThreadsService
from app.tools.threads.storage import render_text
from app.workers import threads as worker_module


def config(**kwargs: object) -> ThreadsConfig:
    return ThreadsConfig(_env_file=None, **kwargs)


def post(identifier: str = "one", replies: int = 4) -> ThreadsPost:
    return ThreadsPost(
        post_id=identifier,
        url=f"https://www.threads.com/@sample/post/{identifier}",
        username="sample",
        text="Useful travel tips",
        reply_count=replies,
    )


def request(**kwargs: object) -> ThreadsRequest:
    return ThreadsRequest.model_validate({"query": "travel tips", **kwargs})


def test_config_reads_shared_environment_and_masks_credentials(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        'THREADS_ACCOUNTS=\'[{"id":"acc_01","password":"sample-secret","proxy":"http://u:p@localhost:8080"}]\'\n'
        "THREADS_SESSIONS_DIR=.local/threads/sessions\n",
        encoding="utf-8",
    )
    # Clear the test harness override to exercise dotenv parsing.
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {}, clear=True):
        loaded = ThreadsConfig(_env_file=env)
    assert loaded.accounts[0].password.get_secret_value() == "sample-secret"
    assert loaded.sessions_dir.is_absolute()
    assert "sample-secret" not in repr(loaded)
    assert "u:p" not in repr(loaded.accounts[0])
    with pytest.raises(ValidationError):
        config(accounts=[ThreadsAccount(id="../escape")])
    with pytest.raises(ValidationError):
        config(accounts=[ThreadsAccount(id="same"), ThreadsAccount(id="SAME")])
    with pytest.raises(ValidationError):
        config(min_delay_seconds=4, max_delay_seconds=1)


def test_parser_extracts_search_roots_media_and_nested_comments() -> None:
    source = {
        "searchResults": {
            "edges": [
                {
                    "node": {
                        "thread": {
                            "thread_items": [
                                {
                                    "post": {
                                        "pk": "one",
                                        "code": "abcdef",
                                        "user": {"username": "sample"},
                                        "caption": {"text": "Travel advice"},
                                        "text_post_app_info": {"direct_reply_count": 3},
                                        "image_versions2": {
                                            "candidates": [
                                                {
                                                    "url": "https://cdn.example/image.jpg",
                                                    "width": 100,
                                                    "height": 100,
                                                },
                                            ]
                                        },
                                    }
                                },
                                {
                                    "post": {
                                        "pk": "quoted",
                                        "code": "quoted1",
                                        "user": {"username": "other"},
                                    }
                                },
                            ]
                        }
                    }
                }
            ]
        }
    }
    posts = extract_search_posts([source, source], "travel")
    assert len(posts) == 1
    assert posts[0].post_id == "one"
    assert posts[0].reply_count == 3
    assert posts[0].images == ["https://cdn.example/image.jpg"]
    assert extract_search_posts([{"searchResults": {"edges": [None, {}]}}], "travel") == []
    comments = extract_comments(
        [
            [
                {
                    "pk": "parent",
                    "user": {"username": "a"},
                    "caption": {"text": "A suggestion"},
                    "text_post_app_info": {"is_reply": True, "reply_level": 1},
                },
                {
                    "pk": "child",
                    "user": {"username": "b"},
                    "caption": {"text": "A correction"},
                    "text_post_app_info": {"reply_level": 2, "reply_to_author": {"username": "a"}},
                },
            ]
        ]
    )
    assert comments[1].parent_id == "parent"
    assert comments[1].depth == 2
    assert comments[1].reply_to_username == "a"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.threads.com/",
        "https://threads.com.attacker.example/",
        "https://127.0.0.1/",
        "file:///etc/passwd",
        "https://www.threads.com:8443/",
        "https://user:pass@www.threads.com/",
    ],
)
def test_browser_blocks_untrusted_destinations(url: str) -> None:
    assert not allowed_browser_url(url)


def test_proxy_credentials_are_separated_from_server_url() -> None:
    assert allowed_browser_url("https://www.threads.com/search/?q=travel")
    assert playwright_proxy("http://user:pass%40word@proxy.example:8080") == {
        "server": "http://proxy.example:8080",
        "username": "user",
        "password": "pass@word",
    }
    with pytest.raises(ThreadsError, match="valid Threads proxy"):
        playwright_proxy("file:///tmp/proxy")


@pytest.mark.asyncio
async def test_missing_sessions_never_fall_back_to_anonymous(tmp_path: Path) -> None:
    with pytest.raises(ThreadsError) as raised:
        async with open_crawler(
            config(accounts=[ThreadsAccount(id="acc_01")], sessions_dir=tmp_path)
        ):
            pytest.fail("A missing session must prevent browser startup")
    assert raised.value.code == "THREADS_REAUTH_REQUIRED"


@pytest.mark.asyncio
async def test_search_waits_for_delayed_data_instead_of_saving_an_empty_collection() -> None:
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value={"top": 0, "height": 900, "viewport": 900}),
        wait_for_timeout=AsyncMock(),
    )
    crawler = PlaywrightThreadsCrawler([page])

    @asynccontextmanager
    async def sources(_page, _url):
        yield []

    crawler._sources = sources
    response = {
        "searchResults": {
            "edges": [
                {
                    "node": {
                        "thread": {
                            "thread_items": [
                                {
                                    "post": {
                                        "pk": "late-post",
                                        "code": "abcdef1",
                                        "user": {"username": "fixture"},
                                        "caption": {"text": "A delayed result"},
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
        }
    }
    crawler._scripts = AsyncMock(side_effect=[[], [], [], [], [response]])
    posts = await crawler.search("travel", 1, "recent")
    assert [item.post_id for item in posts] == ["late-post"]
    assert crawler._scripts.await_count == 5


@pytest.mark.asyncio
@pytest.mark.parametrize("valid_response", [True, False])
async def test_search_only_accepts_empty_results_after_a_valid_response(
    valid_response: bool,
) -> None:
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value={"top": 0, "height": 900, "viewport": 900}),
        wait_for_timeout=AsyncMock(),
    )
    crawler = PlaywrightThreadsCrawler([page])

    @asynccontextmanager
    async def sources(_page, _url):
        yield []

    crawler._sources = sources
    crawler._scripts = AsyncMock(
        return_value=[{"searchResults": {"edges": []}}] if valid_response else []
    )
    if valid_response:
        assert await crawler.search("travel", 1, "recent") == []
    else:
        with pytest.raises(ThreadsError) as error:
            await crawler.search("travel", 1, "recent")
        assert error.value.code == "THREADS_SEARCH_UNAVAILABLE"


def search_source(count: int, *, more: bool) -> dict[str, object]:
    return {
        "searchResults": {
            "edges": [
                {
                    "node": {
                        "thread": {
                            "thread_items": [
                                {
                                    "post": {
                                        "pk": f"post-{index}",
                                        "code": f"code{index:06}",
                                        "user": {"username": "fixture"},
                                        "caption": {"text": "Source text"},
                                    }
                                }
                            ]
                        }
                    }
                }
                for index in range(count)
            ],
            "page_info": {"has_next_page": more},
        }
    }


@pytest.mark.asyncio
async def test_search_continues_past_stale_counts_until_it_reaches_the_requested_limit() -> None:
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value={"top": 0, "height": 12000, "viewport": 900}),
        wait_for_timeout=AsyncMock(),
    )
    crawler = PlaywrightThreadsCrawler([page])

    @asynccontextmanager
    async def sources(_page, _url):
        yield []

    crawler._sources = sources
    crawler._scripts = AsyncMock(
        side_effect=[[search_source(18, more=True)]] * 6 + [[search_source(25, more=True)]]
    )
    warnings: list[str] = []
    posts = await crawler.search("travel", 25, "top", on_warning=warnings.append)
    assert len(posts) == 25
    assert warnings == []


@pytest.mark.asyncio
async def test_search_warns_when_threads_confirms_fewer_results_are_available() -> None:
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value={"top": 1100, "height": 2000, "viewport": 900}),
        wait_for_timeout=AsyncMock(),
    )
    crawler = PlaywrightThreadsCrawler([page])

    @asynccontextmanager
    async def sources(_page, _url):
        yield []

    crawler._sources = sources
    crawler._scripts = AsyncMock(return_value=[search_source(18, more=False)])
    warnings: list[str] = []
    posts = await crawler.search("travel", 25, "top", on_warning=warnings.append)
    assert len(posts) == 18
    assert len(warnings) == 1
    assert "18 of 25" in warnings[0] and "no further results" in warnings[0]


@pytest.mark.asyncio
async def test_latest_network_pagination_takes_precedence_over_initial_page_metadata() -> None:
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value={"top": 0, "height": 900, "viewport": 900}),
        wait_for_timeout=AsyncMock(),
    )
    crawler = PlaywrightThreadsCrawler([page])

    @asynccontextmanager
    async def sources(_page, _url):
        yield [search_source(18, more=True)]

    crawler._sources = sources
    crawler._scripts = AsyncMock(
        side_effect=[[search_source(18, more=False)]] * 4 + [[search_source(25, more=False)]]
    )
    assert len(await crawler.search("travel", 25, "top")) == 25
    assert (
        search_has_next_page([search_source(18, more=True), search_source(25, more=False)]) is False
    )
    assert search_has_next_page([{"searchResults": {"edges": []}}]) is None


@pytest.mark.asyncio
async def test_pipeline_preserves_search_shortfall_warnings_without_ai_filtering() -> None:
    async def search(_keyword: str, _limit: int, _type: str, *, on_warning) -> list[ThreadsPost]:
        on_warning(
            "Collected 18 of 25 requested unique posts: Threads reported no further results."
        )
        return [post(str(index)) for index in range(18)]

    crawler = SimpleNamespace(search=AsyncMock(side_effect=search), comments=AsyncMock())
    result = await ThreadsPipeline(config(min_delay_seconds=0, max_delay_seconds=0)).run(
        request(
            keywords=["travel"],
            expand_query=False,
            pre_filter=False,
            curate=False,
            include_comments=False,
        ),
        AsyncMock(),
        AsyncMock(return_value=False),
        crawler=crawler,
    )
    assert len(result.posts) == 18
    assert len(result.warnings) == 1 and result.warnings[0].startswith(
        "Keyword 1: Collected 18 of 25"
    )


@pytest.mark.asyncio
async def test_pipeline_deduplicates_filters_and_curates_with_comment_context() -> None:
    crawler = SimpleNamespace(
        search=AsyncMock(side_effect=[[post(), post("two", 0)], [post()]]),
        comments=AsyncMock(
            return_value=[ThreadsComment(id="c", username="a", text="A correction")]
        ),
    )
    analysis = ThreadsAnalysis(
        is_relevant=True, confidence_score=0.9, topic="Travel", summary="A useful summary"
    )
    ai = SimpleNamespace(
        keywords=AsyncMock(return_value=["travel", "advice"]),
        filter=AsyncMock(return_value={"one"}),
        curate=AsyncMock(return_value=analysis),
    )
    result = await ThreadsPipeline(config(min_delay_seconds=0, max_delay_seconds=0)).run(
        request(keywords=["travel", "advice"], pre_filter=True, curate=True),
        AsyncMock(),
        AsyncMock(return_value=False),
        crawler=crawler,
        ai=ai,
    )
    assert len(result.posts) == 1
    assert result.posts[0].search_keywords == ["travel", "advice"]
    assert result.total_comments == 1
    assert result.curated_post_ids == ["one"]
    assert ai.curate.await_args.args[1].comments[0].text == "A correction"
    ai.keywords.assert_not_awaited()
    crawler.comments.assert_awaited_once()


@pytest.mark.asyncio
async def test_pipeline_without_ai_or_comments_never_calls_providers() -> None:
    ai = SimpleNamespace(keywords=AsyncMock(), filter=AsyncMock(), curate=AsyncMock())
    crawler = SimpleNamespace(search=AsyncMock(return_value=[post()]), comments=AsyncMock())
    result = await ThreadsPipeline(config(min_delay_seconds=0, max_delay_seconds=0)).run(
        request(expand_query=False, pre_filter=False, curate=False, include_comments=False),
        AsyncMock(),
        AsyncMock(return_value=False),
        crawler=crawler,
        ai=ai,
    )
    assert result.keywords == ["travel tips"]
    assert result.curated_post_ids == []
    ai.keywords.assert_not_awaited()
    ai.filter.assert_not_awaited()
    ai.curate.assert_not_awaited()
    crawler.comments.assert_not_awaited()


@pytest.mark.asyncio
async def test_pipeline_supports_unlimited_comments_and_strictness() -> None:
    crawler = SimpleNamespace(
        search=AsyncMock(return_value=[post("p1", 5), post("p2", 3)]),
        comments=AsyncMock(
            return_value=[ThreadsComment(id="c1", username="user1", text="comment 1")]
        ),
    )
    ai = SimpleNamespace(
        keywords=AsyncMock(),
        filter=AsyncMock(return_value={"p1", "p2"}),
        curate=AsyncMock(
            return_value=ThreadsAnalysis(
                is_relevant=True, confidence_score=0.95, topic="Travel", summary="Great"
            )
        ),
    )
    req = request(
        keywords=["travel"],
        include_comments=True,
        max_comment_posts=-1,
        max_comments_per_post=-1,
        pre_filter=True,
        pre_filter_strictness="medium",
    )
    result = await ThreadsPipeline(config(min_delay_seconds=0, max_delay_seconds=0)).run(
        req, AsyncMock(), AsyncMock(return_value=False), crawler=crawler, ai=ai
    )
    assert len(result.posts) == 2
    assert crawler.comments.await_count == 2
    crawler.comments.assert_any_await("https://www.threads.com/@sample/post/p1", -1)
    crawler.comments.assert_any_await("https://www.threads.com/@sample/post/p2", -1)


@pytest.mark.asyncio
async def test_pipeline_cancellation_stops_before_browser_work() -> None:
    crawler = SimpleNamespace(search=AsyncMock())
    with pytest.raises(ThreadsCancelled):
        await ThreadsPipeline(config()).run(
            request(),
            AsyncMock(),
            AsyncMock(return_value=True),
            crawler=crawler,
        )
    crawler.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_groq_validates_external_json_and_never_exposes_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "groq_api_key", SecretStr("test-api-key"))
    sent: list[dict[str, object]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        sent.append(json.loads(req.content))
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"keywords":["short phrase"]}'}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await GroqThreadsAI(config(), client).keywords("a long travel question") == [
            "short phrase"
        ]
    assert sent[0]["response_format"] == {"type": "json_object"}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(401, text="test-api-key"))
    ) as client:
        with pytest.raises(ThreadsError) as error:
            await GroqThreadsAI(config(), client).keywords("travel")
        assert "test-api-key" not in str(error.value)
        assert error.value.code == "GROQ_UNAVAILABLE"


@pytest.fixture
def repository() -> ThreadsRepository:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    # Execute real SQL in SQLite while adapting only AsyncSession's I/O boundary.
    adapter = Mock(spec=AsyncSession)
    for method in ("scalar", "scalars", "get", "refresh", "commit", "rollback", "delete"):
        setattr(adapter, method, AsyncMock(side_effect=getattr(session, method)))
    adapter.add.side_effect = session.add
    yield ThreadsRepository(adapter)
    session.close()
    engine.dispose()


def user(role: str = "member") -> User:
    return User(id=uuid4(), username=f"user-{uuid4().hex}", password_hash="test", role=role)


@pytest.mark.asyncio
async def test_repository_enforces_ownership_idempotency_and_cancellation(
    repository: ThreadsRepository,
) -> None:
    owner, other, admin = user(), user(), user("admin")
    run = await repository.create(owner, request(visibility="private"), "threads-run-1")
    assert (
        await repository.create(owner, request(visibility="private"), "threads-run-1")
    ).id == run.id
    with pytest.raises(ThreadsError) as conflict:
        await repository.create(owner, request(query="another"), "threads-run-1")
    assert conflict.value.code == "IDEMPOTENCY_CONFLICT"
    assert (await repository.get(run.id, admin)).id == run.id
    assert await repository.list(other, 20, 0) == []
    with pytest.raises(ThreadsError) as denied:
        await repository.get(run.id, other)
    assert denied.value.status_code == 404
    cancelled = await repository.cancel(run.id, owner)
    assert cancelled.status == "cancelled"
    assert await repository.claim_next("worker") is None


@pytest.mark.asyncio
async def test_repository_finalization_honors_cancel_and_recovers_interrupted_jobs(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    queued = await repository.create(owner, request(), None)
    running = await repository.claim_next("worker")
    assert running.id == queued.id
    await repository.cancel(running.id, owner)
    await repository.finish(running.id, error=ThreadsError("TEST_ERROR", "A safe error"))
    assert (await repository.get(running.id, owner)).status == "cancelled"
    second = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    await repository.recover_interrupted()
    failed = await repository.get(second.id, owner)
    assert failed.status == "failed"
    assert failed.error_code == "WORKER_INTERRUPTED"


@pytest.mark.asyncio
async def test_repository_persists_results_and_does_not_cancel_completed_runs(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    queued = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    result = ThreadsResult(
        query="travel tips",
        keywords=["travel"],
        posts=[post()],
        duration_seconds=1.5,
    )
    result.posts[0].comments = [
        ThreadsComment(
            id="comment-one",
            username="reader",
            text="A nested reply",
            depth=2,
            parent_id="parent-one",
        )
    ]
    result.total_comments = 1
    await repository.finish(queued.id, result=result.model_dump(mode="json"))
    stored = to_response(await repository.get(queued.id, owner))
    assert stored.status == "completed"
    assert stored.progress == 1
    assert stored.result.posts[0].post_id == "one"
    assert stored.result.posts[0].comments[0].parent_id == "parent-one"
    assert "result" not in (await repository.get(queued.id, owner)).details
    for model in (ThreadsResultRecord, ThreadsPostRecord, ThreadsCommentRecord):
        assert await repository.session.scalar(select(func.count()).select_from(model)) == 1
    cancelled = await repository.cancel(queued.id, owner)
    assert cancelled.status == "completed"
    assert not cancelled.cancel_requested


@pytest.mark.asyncio
async def test_threads_config_exposes_only_safe_readiness_and_defaults(tmp_path: Path) -> None:
    loaded = config(
        enabled=True,
        sessions_dir=tmp_path,
        accounts=[ThreadsAccount(id="acc_01", password=SecretStr("fixture-secret"))],
    )
    service = ThreadsService(SimpleNamespace(), loaded)
    response = service.get_config()
    assert not response.accounts_ready
    assert "fixture-secret" not in response.model_dump_json()
    assert "accounts" not in response.model_dump()
    assert response.defaults.max_posts_per_keyword == 25
    assert response.limits["posts_per_keyword"] == 100


@pytest.mark.asyncio
async def test_export_rejects_results_that_are_not_completed(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(), None)
    service = ThreadsService(repository, config())
    with pytest.raises(ThreadsError) as raised:
        await service.export(run.id, owner)
    assert raised.value.code == "RESULT_NOT_READY"


@pytest.mark.asyncio
async def test_service_rejects_disabled_tool_and_missing_ai_before_queueing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = SimpleNamespace(create=AsyncMock())
    with pytest.raises(ThreadsError) as disabled:
        await ThreadsService(repo, config(enabled=False)).create(user(), request(), None)
    assert disabled.value.code == "THREADS_DISABLED"
    monkeypatch.setattr(settings, "groq_api_key", None)
    with pytest.raises(ThreadsError) as missing_key:
        await ThreadsService(repo, config(enabled=True, anonymous=True)).create(
            user(), request(), None
        )
    assert missing_key.value.code == "GROQ_NOT_CONFIGURED"
    repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_uses_env_credentials_and_saves_only_authenticated_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.tools.threads.auth as auth_module

    username, password = AsyncMock(), AsyncMock()
    find = AsyncMock(side_effect=[username, password])
    monkeypatch.setattr(auth_module, "first_visible", find)
    await submit_credentials(
        AsyncMock(),
        ThreadsAccount(
            id="acc_01",
            username=SecretStr("sample"),
            password=SecretStr("test-password"),
        ),
    )
    username.fill.assert_awaited_once_with("sample")
    password.fill.assert_awaited_once_with("test-password")
    state = {
        "cookies": [{"name": "sessionid", "value": "test-session", "domain": ".threads.com"}],
        "origins": [],
    }
    target = tmp_path / "sessions" / "acc_01.json"
    await save_session(SimpleNamespace(storage_state=AsyncMock(return_value=state)), target)
    assert json.loads(target.read_text()) == state
    with pytest.raises(ThreadsError):
        await save_session(
            SimpleNamespace(storage_state=AsyncMock(return_value={"cookies": []})), target
        )
    assert json.loads(target.read_text()) == state


@pytest.mark.asyncio
async def test_worker_runs_registered_tool_and_persists_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    run = SimpleNamespace(
        id=run_id,
        details={"request": request().model_dump(mode="json")},
        owner_id=uuid4(),
    )
    repo = SimpleNamespace(
        claim_next=AsyncMock(return_value=run),
        finish=AsyncMock(),
        get_existing_post_ids=AsyncMock(return_value=set()),
    )

    @asynccontextmanager
    async def session_factory():
        yield SimpleNamespace()

    class FakeTool:
        name = "threads"

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def run(self, payload: dict[str, object]) -> dict[str, object]:
            assert payload["query"] == "travel tips"
            return {"posts": []}

    monkeypatch.setattr(worker_module, "async_session_factory", session_factory)
    monkeypatch.setattr(worker_module, "ThreadsRepository", lambda _: repo)
    monkeypatch.setattr(worker_module, "ThreadsTool", FakeTool)
    assert await worker_module.ThreadsWorker(config()).run_once()
    assert repo.finish.await_args.kwargs["result"] == {"posts": []}


@pytest.mark.asyncio
async def test_worker_cancellation_monitor_interrupts_long_browser_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = worker_module.ThreadsWorker(config(worker_poll_seconds=0.1))
    monkeypatch.setattr(worker, "_cancelled", AsyncMock(return_value=True))
    execution = asyncio.create_task(asyncio.sleep(60))
    await worker._monitor(uuid4(), execution, None)
    with pytest.raises(asyncio.CancelledError):
        await execution


@pytest.mark.asyncio
async def test_browser_execution_forwards_progress_and_cleans_up_on_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller_thread = threading.get_ident()
    started = asyncio.Event()
    closed = threading.Event()
    checkpoint_saved = asyncio.Event()

    async def save_checkpoint(result: ThreadsResult) -> None:
        assert threading.get_ident() == caller_thread
        assert result.posts[0].post_id == "one"
        checkpoint_saved.set()

    async def progress(_stage: str, _value: float) -> None:
        assert threading.get_ident() == caller_thread
        started.set()

    class FakeTool:
        name = "threads"

        def __init__(
            self,
            _config: ThreadsConfig,
            on_progress,
            is_cancelled,
            on_snapshot,
            **_kwargs: object,
        ) -> None:
            self.on_progress = on_progress
            self.is_cancelled = is_cancelled
            self.on_snapshot = on_snapshot

        async def run(self, _payload: dict[str, object]) -> dict[str, object]:
            if sys.platform == "win32":
                assert threading.get_ident() != caller_thread
            try:
                await self.on_snapshot(
                    ThreadsResult(query="travel", keywords=[], posts=[post()], duration_seconds=1)
                )
                await self.on_progress("searching", 0.2)
                assert not await self.is_cancelled()
                await asyncio.sleep(60)
            finally:
                closed.set()
            return {}

    monkeypatch.setattr(worker_module, "ThreadsTool", FakeTool)
    execution = asyncio.create_task(
        worker_module.ThreadsWorker(config())._execute_tool(
            {},
            progress,
            AsyncMock(return_value=False),
            save_checkpoint,
        )
    )
    await asyncio.wait_for(started.wait(), timeout=5)
    execution.cancel()
    with pytest.raises(asyncio.CancelledError):
        await execution
    assert closed.is_set()
    assert checkpoint_saved.is_set()


@pytest.mark.asyncio
async def test_public_sessions_are_readable_but_only_owner_and_admin_can_manage(
    repository: ThreadsRepository,
) -> None:
    owner, reader, admin = user(), user(), user("admin")
    run = await repository.create(owner, request(), None)
    assert (await repository.get(run.id, reader)).id == run.id
    listed = await ThreadsService(repository, config()).list(reader, 20, 0)
    assert listed[0].visibility == "public"
    assert listed[0].owner.id == owner.id
    assert listed[0].result is None
    assert not listed[0].can_manage
    for operation in (
        repository.cancel(run.id, reader),
        repository.update_visibility(run.id, reader, "private"),
        repository.request_delete(run.id, reader),
    ):
        with pytest.raises(ThreadsError) as denied:
            await operation
        assert denied.value.status_code == 404
    await repository.update_visibility(run.id, owner, "private")
    assert await repository.list(reader, 20, 0) == []
    with pytest.raises(ThreadsError):
        await ThreadsService(repository, config()).export(run.id, reader)
    assert (await repository.get(run.id, admin)).id == run.id
    await repository.update_visibility(run.id, admin, "public")
    assert (await repository.get(run.id, reader)).threads_result.visibility == "public"


@pytest.mark.asyncio
async def test_pipeline_commits_selected_ids_before_comments_and_preserves_partial_failure(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(pre_filter=True), None)
    await repository.claim_next("worker")

    async def collect(url: str, _limit: int) -> list[ThreadsComment]:
        saved = to_response(await repository.get(run.id, owner))
        assert [item.post_id for item in saved.result.posts] == ["one", "two"]
        if url.endswith("two"):
            assert saved.result.posts[0].comments[0].id == "first-comment"
            raise ThreadsError("COMMENTS_FAILED", "Comments unavailable")
        return [ThreadsComment(id="first-comment", username="reader", text="Saved response")]

    crawler = SimpleNamespace(
        search=AsyncMock(return_value=[post("one", 5), post("two", 4), post("rejected")]),
        comments=AsyncMock(side_effect=collect),
    )
    ai = SimpleNamespace(keywords=AsyncMock(), filter=AsyncMock(return_value={"one", "two"}))
    with pytest.raises(ThreadsError) as failed:
        await ThreadsPipeline(config(min_delay_seconds=0, max_delay_seconds=0)).run(
            request(keywords=["travel"], pre_filter=True),
            AsyncMock(),
            AsyncMock(return_value=False),
            crawler=crawler,
            ai=ai,
            on_snapshot=lambda result: repository.save_snapshot(run.id, result),
        )
    await repository.finish(run.id, error=failed.value)
    response = await ThreadsService(repository, config()).export(run.id, owner)
    assert response.status == "failed"
    assert response.post_count == 2
    assert response.comment_count == 1
    assert response.result.total_comments == 1
    assert "rejected" not in [item.post_id for item in response.result.posts]


@pytest.mark.asyncio
async def test_saved_data_survives_restart_and_cannot_be_written_after_cancel(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    result = ThreadsResult(query="travel", keywords=["travel"], posts=[post()], duration_seconds=1)
    await repository.save_snapshot(run.id, result)
    await repository.save_snapshot(run.id, result)
    assert await repository.session.scalar(select(func.count()).select_from(ThreadsPostRecord)) == 1
    await repository.recover_interrupted()
    saved = to_response(await repository.get(run.id, owner))
    assert saved.status == "failed"
    assert saved.result.posts[0].post_id == "one"
    with pytest.raises(ThreadsCancelled):
        await repository.save_snapshot(run.id, result)


def fake_store() -> SimpleNamespace:
    return SimpleNamespace(available=True, upload=AsyncMock(), delete=AsyncMock())


@pytest.mark.asyncio
async def test_archive_failure_keeps_cloud_id_and_cleanup_retries_before_hard_deletion(
    repository: ThreadsRepository,
) -> None:
    owner, reader = user(), user()
    run = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    result = ThreadsResult(query="travel", keywords=["travel"], posts=[post()], duration_seconds=1)
    result.posts[0].comments = [ThreadsComment(id="c1", username="reader", text="Saved")]
    result.total_comments = 1
    await repository.finish(run.id, result=result.model_dump(mode="json"))
    store = fake_store()
    store.upload.side_effect = ThreadsError("CLOUDINARY_UPLOAD_FAILED", "Unknown upload outcome")
    artifacts = ThreadsArtifacts(repository, store)
    assert await artifacts.run_once()
    failed = await repository.get(run.id, owner)
    assert failed.threads_result.archive_public_id == archive_public_id(run.id)
    assert failed.threads_result.next_storage_attempt_at is not None
    assert to_response(failed).result.posts[0].comments[0].id == "c1"

    await repository.request_delete(run.id, owner)
    with pytest.raises(ThreadsError):
        await repository.get(run.id, reader)
    store.delete.side_effect = ThreadsError("CLOUDINARY_DELETE_FAILED", "Try again")
    assert await artifacts.run_once()
    assert (await repository.get(run.id, owner)).threads_result.deletion_requested
    assert not await artifacts.run_once()
    await repository.request_delete(run.id, owner)
    store.delete.side_effect = None
    assert await artifacts.run_once()
    store.delete.assert_awaited_with(archive_public_id(run.id))
    for model in (ToolRun, ThreadsResultRecord, ThreadsPostRecord, ThreadsCommentRecord):
        assert await repository.session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.asyncio
async def test_cloud_archive_is_one_file_and_visibility_change_reuses_the_asset(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    result = ThreadsResult(query="travel", keywords=["travel"], posts=[post()], duration_seconds=1)
    await repository.finish(run.id, result=result.model_dump(mode="json"))
    store = fake_store()
    artifacts = ThreadsArtifacts(repository, store)
    assert await artifacts.run_once()
    assert (await repository.get(run.id, owner)).threads_result.archive_status == "ready"
    first_id, content = store.upload.await_args.args
    assert first_id.endswith(f"{run.id}.txt")
    assert str(run.id) in content and "Useful travel tips" in content
    assert not await artifacts.run_once()
    await repository.update_visibility(run.id, owner, "private")
    assert await artifacts.run_once()
    assert store.upload.await_args.args[0] == first_id
    assert '"visibility": "private"' in store.upload.await_args.args[1]


@pytest.mark.asyncio
async def test_unconfigured_cloud_does_not_block_local_download_or_deleting_unuploaded_session(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    result = ThreadsResult(query="travel", keywords=["travel"], posts=[post()], duration_seconds=1)
    await repository.finish(run.id, result=result.model_dump(mode="json"))
    store = fake_store()
    store.available = False
    artifacts = ThreadsArtifacts(repository, store)
    assert await artifacts.run_once()
    assert (await repository.get(run.id, owner)).threads_result.archive_public_id is None
    exported = await ThreadsService(repository, config()).export(run.id, owner)
    assert "Useful travel tips" in render_text(exported)
    await repository.request_delete(run.id, owner)
    assert await artifacts.run_once()
    store.delete.assert_not_awaited()
    assert await repository.session.scalar(select(func.count()).select_from(ToolRun)) == 0


@pytest.mark.asyncio
async def test_deleting_active_session_waits_for_worker_and_rejects_further_snapshots(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    result = ThreadsResult(query="travel", keywords=[], posts=[post()], duration_seconds=1)
    await repository.save_snapshot(run.id, result)
    await repository.request_delete(run.id, owner)
    assert await repository.is_cancelled(run.id)
    artifacts = ThreadsArtifacts(repository, fake_store())
    assert not await artifacts.run_once()
    with pytest.raises(ThreadsCancelled):
        await repository.save_snapshot(run.id, result)
    with pytest.raises(ThreadsError) as exporting:
        await ThreadsService(repository, config()).export(run.id, owner)
    assert exporting.value.code == "SESSION_DELETING"
    await repository.finish(run.id)
    assert await artifacts.run_once()
    with pytest.raises(ThreadsError):
        await repository.get(run.id, owner)


@pytest.mark.asyncio
async def test_cloudinary_uploads_authenticated_raw_text_and_uses_signed_deletion() -> None:
    import hashlib
    from urllib.parse import parse_qs

    config = CloudinaryConfig(
        _env_file=None, cloud_name="fixture", api_key="fixture-key", api_secret="fixture-secret"
    )
    public_id = archive_public_id(uuid4())
    received: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        received.append(request)
        body = request.content.decode()
        assert "fixture-secret" not in body
        if request.url.path.endswith("upload"):
            assert 'name="type"\r\n\r\nauthenticated' in body
            assert 'name="overwrite"\r\n\r\ntrue' in body
            assert 'name="backup"\r\n\r\nfalse' in body
            assert "THREADS SESSION" in body
            assert "text/plain; charset=utf-8" in body
            return httpx.Response(
                200, json={"public_id": public_id, "resource_type": "raw", "type": "authenticated"}
            )
        data = {key: values[0] for key, values in parse_qs(body).items()}
        signature = data.pop("signature")
        assert data.pop("api_key") == "fixture-key"
        message = "&".join(f"{key}={value}" for key, value in sorted(data.items()))
        assert signature == hashlib.sha256((message + "fixture-secret").encode()).hexdigest()
        assert data["type"] == "authenticated" and data["invalidate"] == "true"
        return httpx.Response(200, json={"result": "not found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        store = CloudinaryTextStore(config, client)
        await store.upload(public_id, "THREADS SESSION")
        await store.delete(public_id)
    assert received[0].url.path == "/v1_1/fixture/raw/upload"
    assert received[1].url.path == "/v1_1/fixture/raw/destroy"


@pytest.mark.asyncio
async def test_cloudinary_rejects_invalid_provider_responses_without_exposing_secrets() -> None:
    config = CloudinaryConfig(
        _env_file=None, cloud_name="fixture", api_key="fixture-key", api_secret="fixture-secret"
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(500, text="fixture-secret"))
    ) as client:
        store = CloudinaryTextStore(config, client)
        for operation in (store.upload("fixture.txt", "text"), store.delete("fixture.txt")):
            with pytest.raises(ThreadsError) as error:
                await operation
            assert "fixture-secret" not in str(error.value)


@pytest.mark.asyncio
async def test_text_preserves_metadata_media_analysis_and_untrusted_comment_text(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(visibility="private"), None)
    await repository.claim_next("worker")
    sample = post()
    sample.text = "Literal ``` and <script>alert(1)</script>"
    sample.images = ["https://example.com/image.jpg"]
    sample.comments = [
        ThreadsComment(
            id="nested", username="reader", text="Nested ``` response", parent_id="parent", depth=2
        )
    ]
    sample.ai_analysis = ThreadsAnalysis(
        is_relevant=True,
        confidence_score=1,
        topic="Travel",
        summary="Summary",
        key_entities=["Place"],
    )
    result = ThreadsResult(
        query="travel",
        keywords=["travel"],
        posts=[sample],
        total_comments=1,
        duration_seconds=1,
        curated_post_ids=[sample.post_id],
    )
    await repository.finish(run.id, result=result.model_dump(mode="json"))
    document = render_text(to_response(await repository.get(run.id, owner)))
    for expected in (
        str(run.id),
        str(owner.id),
        '"visibility": "private"',
        "| Literal ``` and <script>alert(1)</script>",
        sample.text,
        sample.images[0],
        '"parent_id": "parent"',
        '"depth": 2',
        "Nested ``` response",
        '"key_entities"',
        '"curated_post_ids"',
    ):
        assert expected in document


def test_dom_cleanup_removes_ui_fragments_without_changing_legitimate_dates_or_words() -> None:
    text = dom_comment_text(
        "fixture",
        [
            "fixture",
            "12/18/25",
            "A useful answer.",
            "Translate",
            "2d",
            "Reply",
            "Our meeting on 12/18/25 was helpful. Translate this sentence.",
            "Thanks! ☺️",
        ],
    )
    assert (
        text
        == "A useful answer.\nOur meeting on 12/18/25 was helpful. Translate this sentence.\nThanks! ☺️"
    )
    polluted = {"id": "dom_fixture", "text": "12/18/25 A useful answer. Translate"}
    assert clean_stored_comment(polluted)["text"] == "A useful answer."
    assert polluted["text"].startswith("12/18/25")
    structured = {**polluted, "id": "source-comment"}
    assert clean_stored_comment(structured) == structured


@pytest.mark.asyncio
async def test_text_export_orders_nested_replies_and_retains_missing_parents_and_cycles(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    sample = post()
    sample.comments = [
        ThreadsComment(
            id="child",
            username="reader",
            text="Child text\nEND POST 1",
            parent_id="parent",
            depth=2,
        ),
        ThreadsComment(
            id="orphan", username="reader", text="Orphan text", parent_id="outside", depth=3
        ),
        ThreadsComment(
            id="parent", username="reader", text="Parent text", parent_id=sample.post_id
        ),
        ThreadsComment(
            id="cycle-a", username="reader", text="Cycle A", parent_id="cycle-b", depth=2
        ),
        ThreadsComment(
            id="cycle-b", username="reader", text="Cycle B", parent_id="cycle-a", depth=3
        ),
    ]
    result = ThreadsResult(
        query="travel", keywords=["travel"], posts=[sample], total_comments=5, duration_seconds=1
    )
    await repository.finish(run.id, result=result.model_dump(mode="json"))
    document = render_text(to_response(await repository.get(run.id, owner)))
    assert document.index("| Parent text") < document.index("| Child text")
    assert '"parent_state": "post"' in document
    assert '"parent_id": "parent"' in document and '"depth": 2' in document
    assert (
        '"parent_id": "outside"' in document
        and '"parent_state": "parent_not_collected"' in document
    )
    assert document.count('"id": "cycle-a"') == 1
    assert document.count('"id": "cycle-b"') == 1
    assert "  | END POST 1" in document
    assert document.endswith("END SESSION\n")


@pytest.mark.asyncio
async def test_replacing_legacy_markdown_keeps_both_cloud_ids_until_cleanup_succeeds(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    result = ThreadsResult(query="travel", keywords=[], posts=[post()], duration_seconds=1)
    await repository.finish(run.id, result=result.model_dump(mode="json"))
    stored = await repository.get(run.id, owner)
    legacy_id = f"cyverse/threads/{run.id}.md"
    stored.threads_result.archive_public_id = legacy_id
    await repository.session.commit()
    store = fake_store()
    store.delete.side_effect = ThreadsError("CLOUDINARY_DELETE_FAILED", "Try again")
    artifacts = ThreadsArtifacts(repository, store)
    assert await artifacts.run_once()
    stored = await repository.get(run.id, owner)
    assert stored.threads_result.archive_status == "failed"
    assert stored.threads_result.archive_public_id.endswith(".txt")
    assert stored.threads_result.legacy_archive_public_id == legacy_id
    await repository.request_delete(run.id, owner)
    store.delete.side_effect = None
    assert await artifacts.run_once()
    deleted = [call.args[0] for call in store.delete.await_args_list]
    assert archive_public_id(run.id) in deleted and legacy_id in deleted
    with pytest.raises(ThreadsError):
        await repository.get(run.id, owner)


@pytest.mark.asyncio
async def test_cancel_and_delete_session_wipes_all_data_and_stops_archives(
    repository: ThreadsRepository,
) -> None:
    owner = user()
    run = await repository.create(owner, request(), None)
    await repository.claim_next("worker")
    result = ThreadsResult(
        query="travel",
        keywords=["travel"],
        posts=[
            ThreadsPost(
                post_id="post_cancel_test",
                url="https://www.threads.net/@user/post/1",
                username="test_user",
                text="To be wiped",
                comments=[
                    ThreadsComment(id="c_cancel_1", username="replier", text="reply", depth=1)
                ],
            )
        ],
        duration_seconds=1,
    )
    await repository.save_snapshot(run.id, result)

    # Verify intermediate data exists in DB
    assert await repository.session.scalar(select(func.count()).select_from(ThreadsPostRecord)) == 1
    assert await repository.session.scalar(select(func.count()).select_from(ThreadsCommentRecord)) == 1

    # Cancel session
    cancelled_run = await repository.cancel(run.id, owner)
    assert cancelled_run.cancel_requested
    # Worker finishes cancellation
    await repository.finish(run.id)

    # Verify all posts and comments are completely wiped from database
    assert await repository.session.scalar(select(func.count()).select_from(ThreadsPostRecord)) == 0
    assert await repository.session.scalar(select(func.count()).select_from(ThreadsCommentRecord)) == 0

    reloaded = await repository.get(run.id, owner)
    assert reloaded.status == "cancelled"
    assert reloaded.threads_result.post_count == 0
    assert reloaded.threads_result.comment_count == 0
    assert not reloaded.threads_result.snapshot_ready
    response = to_response(reloaded)
    assert response.result is not None
    assert response.result.posts == []
    assert response.post_count == 0

    # Ensure cancelled post is not treated as existing
    existing = await repository.get_existing_post_ids(owner.id)
    assert "post_cancel_test" not in existing

    # Ensure export is rejected
    service = ThreadsService(repository, config())
    with pytest.raises(ThreadsError) as exc_info:
        await service.export(run.id, owner)
    assert exc_info.value.code == "SESSION_CANCELLED"

    # Ensure archive worker does not upload for cancelled session
    store = fake_store()
    artifacts = ThreadsArtifacts(repository, store)
    assert not await artifacts.run_once()
    store.upload.assert_not_awaited()

    # Now delete the session
    await repository.request_delete(run.id, owner)
    assert await artifacts.run_once()
    # Confirm complete deletion from all database tables
    for model in (ToolRun, ThreadsResultRecord, ThreadsPostRecord, ThreadsCommentRecord):
        assert await repository.session.scalar(select(func.count()).select_from(model)) == 0

