import { ExternalLink, Heart, MessageCircle, Repeat2, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { useLanguage } from "@/lib/i18n/context";
import { filterThreadsPosts, safeThreadsUrl } from "./settings";
import type { ThreadsPost, ThreadsRun } from "./types";
import styles from "./threads.module.css";

function PostCard({ post }: { post: ThreadsPost }) {
  const { t, language } = useLanguage();
  const href = safeThreadsUrl(post.url);
  return (
    <article className={styles.post}>
      <div className={styles.postHeader}>
        <div className={styles.avatar} aria-hidden="true">
          {post.username.slice(0, 1).toUpperCase()}
        </div>
        <div>
          <strong>@{post.username}</strong>
          <small>
            {post.published_at && !Number.isNaN(Date.parse(post.published_at))
              ? new Intl.DateTimeFormat(language === "vi" ? "vi-VN" : "en", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                }).format(new Date(post.published_at))
              : "Threads"}
          </small>
        </div>
        {href && (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.sourceLink}
          >
            {t("threads.openPost")}
            <ExternalLink size={13} />
          </a>
        )}
      </div>
      <p className={styles.postText}>
        {post.text || t("threads.noCaption")}
      </p>
      <div className={styles.postMetrics}>
        <span>
          <Heart size={14} />
          {post.like_count.toLocaleString()} {t("threads.likes")}
        </span>
        <span>
          <MessageCircle size={14} />
          {post.reply_count.toLocaleString()} {t("threads.replies")}
        </span>
        <span>
          <Repeat2 size={14} />
          {post.repost_count.toLocaleString()} {t("threads.reposts")}
        </span>
        {post.images.length + post.videos.length > 0 && (
          <span>
            {post.images.length + post.videos.length} {t("threads.mediaItems")}
          </span>
        )}
      </div>
      <div className={styles.tags}>
        {post.search_keywords.map((keyword) => (
          <span key={keyword}>#{keyword}</span>
        ))}
      </div>
    </article>
  );
}

export function ThreadsResults({ run }: { run: ThreadsRun }) {
  const [search, setSearch] = useState("");
  const [curatedOnly, setCuratedOnly] = useState(false);
  const { t } = useLanguage();
  const posts = useMemo(
    () => filterThreadsPosts(run.result?.posts ?? [], search, curatedOnly),
    [run.result, search, curatedOnly],
  );
  if (!run.result) return null;
  return (
    <section aria-label="Collection results">
      <div className={styles.stats}>
        <div>
          <strong>{run.result.posts.length}</strong>
          <span>{t("threads.postsCollected")}</span>
        </div>
        <div>
          <strong>{run.result.total_comments}</strong>
          <span>{t("threads.comments")}</span>
        </div>
        {run.result.duplicate_count > 0 && <div>
          <strong>{run.result.duplicate_count}</strong>
          <span>Duplicate results skipped or merged</span>
        </div>}
        {run.result.curated_post_ids.length > 0 && (
          <div>
            <strong>{run.result.curated_post_ids.length}</strong>
            <span>{t("threads.curatedPosts")}</span>
          </div>
        )}
        <div>
          <strong>{run.result.duration_seconds.toFixed(1)}s</strong>
          <span>{t("threads.collectionTime")}</span>
        </div>
      </div>
      {run.result.warnings.map((warning) => (
        <p key={warning} className={styles.notice}>
          {warning}
        </p>
      ))}
      <div className={styles.resultToolbar}>
        <label className={styles.filterInput}>
          <Search size={16} />
          <span className="sr-only">{t("threads.filterSearchPlaceholder")}</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("threads.filterSearchPlaceholder")}
          />
        </label>
        {run.result.curated_post_ids.length > 0 && (
          <label className={styles.inlineCheck}>
            <input
              type="checkbox"
              checked={curatedOnly}
              onChange={(event) => setCuratedOnly(event.target.checked)}
            />
            {t("threads.curatedOnly")}
          </label>
        )}
      </div>
      <p className={styles.resultCount}>
        {posts.length} {t("threads.postsShown")} · Keywords: {run.result.keywords.join(", ")}
      </p>
      {posts.length ? (
        <div className={styles.postList}>
          {posts.map((post) => (
            <PostCard key={post.post_id} post={post} />
          ))}
        </div>
      ) : (
        <div className={styles.empty}>
          <Search size={28} />
          <h3>{t("threads.noPostsTitle")}</h3>
          <p>
            {run.result.posts.length
              ? t("threads.noPostsFiltered")
              : t("threads.noPostsEmpty")}
          </p>
        </div>
      )}
    </section>
  );
}
