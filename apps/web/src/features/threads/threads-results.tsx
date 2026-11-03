"use client";

import { ExternalLink, Heart, MessageCircle, Repeat2, Search, MapPin, Compass, CheckCircle2 } from "lucide-react";
import { useMemo, useState, useEffect } from "react";

import { useLanguage } from "@/lib/i18n/context";
import { Badge } from "@/components/ui/badge";
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
  const { t, language } = useLanguage();

  const poiCandidates = run.result?.discovery?.poi_candidates ?? [];
  const hasPois = poiCandidates.length > 0;
  const isTravelMode = run.request.mode === "travel" || run.request.discovery_mode === "evidence_poi";

  const [viewMode, setViewMode] = useState<"poi" | "posts" | "curated">(() => {
    return hasPois ? "poi" : "posts";
  });

  useEffect(() => {
    if (hasPois) {
      setViewMode("poi");
    }
  }, [run.id, hasPois]);

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
        {run.result.duplicate_count > 0 && (
          <div>
            <strong>{run.result.duplicate_count}</strong>
            <span>Duplicate results skipped or merged</span>
          </div>
        )}
        {hasPois && (
          <div>
            <strong>{poiCandidates.length}</strong>
            <span>{language === "vi" ? "Địa điểm phát hiện" : "POIs Discovered"}</span>
          </div>
        )}
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

      {(hasPois || isTravelMode) && (
        <div className={styles.segmentedControl} style={{ maxWidth: 500, margin: "16px 0" }}>
          {hasPois && (
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={viewMode === "poi"}
              onClick={() => setViewMode("poi")}
            >
              {language === "vi" ? `Địa điểm phát hiện (${poiCandidates.length})` : `POIs Discovered (${poiCandidates.length})`}
            </button>
          )}
          <button
            type="button"
            className={styles.segmentedButton}
            data-active={viewMode === "posts"}
            onClick={() => setViewMode("posts")}
          >
            {language === "vi" ? `Bản tin bài viết (${posts.length})` : `Post Feed (${posts.length})`}
          </button>
          <button
            type="button"
            className={styles.segmentedButton}
            data-active={viewMode === "curated"}
            onClick={() => setViewMode("curated")}
          >
            {language === "vi" ? "Bảng phân tích Scraper" : "Analysis Overview"}
          </button>
        </div>
      )}

      {viewMode === "poi" && hasPois ? (
        <div className={styles.placesList} style={{ display: "grid", gap: 14, marginTop: 12 }}>
          {poiCandidates.map((cand, idx) => (
            <article key={cand.id || idx} className={styles.placeCard} style={{ borderLeft: "4px solid var(--blue-600, #2563eb)" }}>
              <div className={styles.placeCardHeader}>
                <div className={styles.placeTitleGroup}>
                  <h4 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>{cand.canonical_name}</h4>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
                    {cand.category && (
                      <Badge variant="outline">{cand.category}</Badge>
                    )}
                    {cand.area && (
                      <Badge variant="secondary"><MapPin size={11} style={{ marginRight: 3 }} />{cand.area}</Badge>
                    )}
                    <Badge variant={cand.verification_status === "verified" ? "default" : "secondary"}>
                      {cand.verification_status === "verified"
                        ? (language === "vi" ? "Đã xác minh qua nhiều nguồn" : "Verified by multiple sources")
                        : (language === "vi" ? "Ứng viên (Cần kiểm chứng)" : "Candidate (Needs verification)")}
                    </Badge>
                    <span style={{ fontSize: 12, color: "var(--muted, #64748b)", alignSelf: "center" }}>
                      {cand.distinct_sources_count} {language === "vi" ? "nguồn độc lập" : "independent sources"}
                    </span>
                  </div>
                </div>
              </div>

              {cand.address && (
                <p style={{ fontSize: 13.5, color: "var(--ink, #0f172a)", margin: "8px 0" }}>
                  📍 <strong>{language === "vi" ? "Địa chỉ trích xuất:" : "Extracted Address:"}</strong> {cand.address}
                </p>
              )}

              {cand.claims && cand.claims.length > 0 && (
                <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
                  <strong style={{ fontSize: 12.5 }}>
                    {language === "vi" ? "Đặc trưng & Đánh giá từ cộng đồng:" : "Features & Community Reviews:"}
                  </strong>
                  {cand.claims.map((claim, cIdx) => (
                    <div key={cIdx} style={{ fontSize: 12, background: "rgba(125, 140, 160, 0.08)", padding: "7px 11px", borderRadius: 6 }}>
                      <span style={{ fontWeight: 600, color: claim.claim_type === "warning" || claim.claim_type === "closure" ? "#dc2626" : "#2563eb" }}>
                        [{claim.claim_type.toUpperCase()}]
                      </span>{" "}
                      <span>{claim.value}</span>
                      <div style={{ fontStyle: "italic", color: "var(--muted, #64748b)", marginTop: 2 }}>
                        “{claim.evidence_text}”
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {cand.mentions && cand.mentions.length > 0 && (
                <div style={{ marginTop: 12, borderTop: "1px dashed var(--line, #e2e8f0)", paddingTop: 8 }}>
                  <small style={{ color: "var(--muted, #64748b)" }}>
                    {language === "vi" ? "Bằng chứng nguồn từ Threads:" : "Evidence mentions from Threads:"}
                  </small>
                  {cand.mentions.slice(0, 3).map((m, mIdx) => (
                    <div key={mIdx} style={{ fontSize: 11.5, color: "var(--muted, #64748b)", marginTop: 3 }}>
                      • Post {m.source_post_id}: “{m.evidence_text}”
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <>
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
        </>
      )}
    </section>
  );
}
