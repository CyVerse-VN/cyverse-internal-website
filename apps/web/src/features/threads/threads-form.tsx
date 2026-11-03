"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ChevronDown, Clock3, KeyRound, Play, RotateCcw, Settings, SlidersHorizontal, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n/context";
import { ImportSessionModal } from "./import-session-modal";
import type { ThreadsAccountItem, ThreadsConfig, ThreadsParameters } from "./types";
import styles from "./threads.module.css";

const POST_LIMIT_OPTIONS = [25, 50, 75, 100];
const COMMENT_LIMIT_OPTIONS = [25, 50, 100];

export function ThreadsForm({
  config,
  parameters,
  query,
  busy,
  error,
  isQueuing = false,
  onQuery,
  onChange,
  onReset,
  onSubmit,
  onRefreshConfig,
}: {
  config: ThreadsConfig | null;
  parameters: ThreadsParameters;
  query: string;
  busy: boolean;
  error: string | null;
  isQueuing?: boolean;
  onQuery: (value: string) => void;
  onChange: (value: Partial<ThreadsParameters>) => void;
  onReset: () => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onRefreshConfig?: () => void;
}) {
  const { t, language } = useLanguage();
  const ready = config?.enabled && config.accounts_ready;
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [accounts, setAccounts] = useState<ThreadsAccountItem[]>([]);

  useEffect(() => {
    let ignore = false;
    fetch("/api/threads/accounts")
      .then((res) => res.json())
      .then((data) => {
        if (!ignore && Array.isArray(data.accounts)) {
          setAccounts(data.accounts);
        }
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, [config]);

  const expiredAccounts = accounts.filter((a) => a.has_session && a.is_expired);

  const isUnlimitedComments = parameters.max_comments_per_post <= 0;
  const activeFilterLevel =
    !parameters.pre_filter || parameters.pre_filter_strictness === "none"
      ? "none"
      : parameters.pre_filter_strictness === "medium"
      ? "medium"
      : "high";

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <div className={styles.sectionTitle}>
        <div>
          <SlidersHorizontal size={17} />
          <h2>{t("threads.configTitle")}</h2>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            className={styles.textButton}
            onClick={() => setShowImportModal(true)}
            title="Import or update Threads session"
          >
            <KeyRound size={13} />
            Session
          </button>
          <button type="button" className={styles.textButton} onClick={onReset}>
            <RotateCcw size={13} />
            {t("threads.reset")}
          </button>
        </div>
      </div>

      {/* Query / Keywords single input */}
      <label className={styles.field} htmlFor="threads-query">
        <span>{t("threads.queryLabel")}</span>
        <textarea
          id="threads-query"
          rows={3}
          maxLength={1000}
          required
          value={query}
          placeholder={t("threads.queryPlaceholder")}
          onChange={(event) => onQuery(event.target.value)}
        />
        <small>{t("threads.queryHint")}</small>
      </label>

      {/* Search & Posts Configuration (Directly exposed, no advanced toggle) */}
      <section className={styles.formSection} aria-labelledby="threads-search-settings-label">
        <h3 id="threads-search-settings-label">
          <SlidersHorizontal size={15} />
          {t("threads.searchOrder")} &amp; {t("threads.postsPerKeyword")}
        </h3>

        {/* Search Order: Segmented control matching AI filter strictness */}
        <div className={styles.segmentedGroup}>
          <span>{t("threads.searchOrder")}</span>
          <div className={styles.segmentedControl}>
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={parameters.search_type === "recent"}
              onClick={() => onChange({ search_type: "recent" })}
            >
              {t("threads.recent")}
            </button>
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={parameters.search_type === "top"}
              onClick={() => onChange({ search_type: "top" })}
            >
              {t("threads.top")}
            </button>
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={parameters.search_type === "both"}
              onClick={() => onChange({ search_type: "both" })}
            >
              {t("threads.searchBoth")}
            </button>
          </div>
        </div>

        {/* Posts per keyword: 25, 50, 75, 100 */}
        <div className={styles.segmentedGroup}>
          <span>{t("threads.postsPerKeyword")}</span>
          <div className={styles.segmentedGrid}>
            {POST_LIMIT_OPTIONS.map((count) => (
              <button
                key={count}
                type="button"
                className={styles.segmentedGridButton}
                data-active={parameters.max_posts_per_keyword === count}
                onClick={() => onChange({ max_posts_per_keyword: count })}
              >
                {count}
              </button>
            ))}
          </div>
          <small className={styles.hint}>{t("threads.postsPerKeywordHint")}</small>
        </div>
      </section>

      {/* Comment Collection Section */}
      <section className={styles.formSection} aria-labelledby="threads-comments-label">
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={parameters.include_comments}
            onChange={(event) => onChange({ include_comments: event.target.checked })}
          />
          <span>
            <strong id="threads-comments-label">{t("threads.commentsLabel")}</strong>
            <small>{t("threads.commentsDesc")}</small>
          </span>
        </label>

        {parameters.include_comments && (
          <fieldset className={styles.commentSettings}>
            <legend className="sr-only">Comment collection limits</legend>

            <div className={styles.segmentedGroup}>
              <span>{t("threads.commentsLimit")}</span>
              <div className={styles.segmentedGrid}>
                {COMMENT_LIMIT_OPTIONS.map((count) => (
                  <button
                    key={count}
                    type="button"
                    className={styles.segmentedGridButton}
                    data-active={parameters.max_comments_per_post === count}
                    onClick={() => onChange({ max_comments_per_post: count })}
                  >
                    {count}
                  </button>
                ))}
                <button
                  type="button"
                  className={styles.segmentedGridButton}
                  data-active={isUnlimitedComments}
                  onClick={() => onChange({ max_comments_per_post: -1 })}
                  title={t("threads.commentsAll")}
                  aria-label={t("threads.commentsAll")}
                >
                  ♾️
                </button>
              </div>
            </div>

            {isUnlimitedComments && (
              <div className={styles.unlimitedNotice}>
                <Sparkles size={15} />
                <span>{t("threads.commentsAllNotice")}</span>
              </div>
            )}
          </fieldset>
        )}
      </section>

      {/* AI Assistance Section */}
      <section className={styles.formSection} aria-labelledby="threads-ai-label">
        <h3 id="threads-ai-label">
          <Sparkles size={15} />
          {t("threads.aiTitle")}
        </h3>
        {!config?.ai_available && config && <p className={styles.hint}>{t("threads.aiUnavailable")}</p>}

        <label className={styles.toggle}>
          <input
            type="checkbox"
            disabled={!config?.ai_available}
            checked={parameters.expand_query}
            onChange={(event) => onChange({ expand_query: event.target.checked })}
          />
          <span>
            <strong>{t("threads.expandQuery")}</strong>
            <small>{t("threads.expandQueryDesc")}</small>
          </span>
        </label>

        {/* When expand_query is checked, allow choosing number of keywords */}
        {parameters.expand_query && (
          <div className={styles.subOptionSection}>
            <span className={styles.subOptionLabel}>{t("threads.keywordsCountLabel")}</span>
            <div className={styles.segmentedControl}>
              {[1, 2, 3, 4, 5].map((count) => (
                <button
                  key={count}
                  type="button"
                  className={styles.segmentedButton}
                  data-active={parameters.keywords_per_query === count}
                  onClick={() => onChange({ keywords_per_query: count })}
                >
                  {count}
                </button>
              ))}
            </div>
            <small className={styles.hint}>{t("threads.keywordsCountHint")}</small>
          </div>
        )}

        {/* AI Filter Strictness level (All / Gentle / Strict) */}
        <div className={styles.segmentedGroup}>
          <span>{t("threads.preFilterStrictness")}</span>
          <div className={styles.segmentedControl}>
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={activeFilterLevel === "none"}
              onClick={() => onChange({ pre_filter: false, pre_filter_strictness: "none" })}
            >
              {t("threads.strictnessNone")}
            </button>
            <button
              type="button"
              className={styles.segmentedButton}
              disabled={!config?.ai_available}
              data-active={activeFilterLevel === "medium"}
              onClick={() => onChange({ pre_filter: true, pre_filter_strictness: "medium" })}
            >
              {t("threads.strictnessMedium")}
            </button>
            <button
              type="button"
              className={styles.segmentedButton}
              disabled={!config?.ai_available}
              data-active={activeFilterLevel === "high"}
              onClick={() => onChange({ pre_filter: true, pre_filter_strictness: "high" })}
            >
              {t("threads.strictnessHigh")}
            </button>
          </div>
          <small className={styles.hint}>
            {activeFilterLevel === "none"
              ? t("threads.strictnessNoneDesc")
              : activeFilterLevel === "medium"
              ? t("threads.strictnessMediumDesc")
              : t("threads.strictnessHighDesc")}
          </small>
        </div>
      </section>

      {/* Advanced Settings Section */}
      <section className={styles.formSection} aria-labelledby="threads-advanced-label">
        <button
          type="button"
          id="threads-advanced-label"
          className={styles.fineTuneToggle}
          onClick={() => setShowAdvanced((prev) => !prev)}
          aria-expanded={showAdvanced}
        >
          <div>
            <SlidersHorizontal size={14} />
            <span>{showAdvanced ? t("threads.hideAdvancedSettings") : t("threads.advancedSettings")}</span>
          </div>
          <ChevronDown size={14} className={showAdvanced ? styles.rotate180 : undefined} />
        </button>

        {showAdvanced && (
          <div className={styles.fineTunePanel}>
            {/* Run Timeout */}
            <div className={styles.segmentedGroup}>
              <span>{t("threads.runTimeoutLabel")}</span>
              <div className={styles.segmentedGrid}>
                {[
                  { label: "30m", val: 1800 },
                  { label: "1h", val: 3600 },
                  { label: "2h", val: 7200 },
                  { label: t("threads.runTimeoutUnlimited"), val: -1 },
                ].map(({ label, val }) => (
                  <button
                    key={val}
                    type="button"
                    className={styles.segmentedGridButton}
                    data-active={parameters.run_timeout_seconds === val}
                    onClick={() => onChange({ run_timeout_seconds: val })}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <small className={styles.hint}>{t("threads.runTimeoutHint")}</small>
              {parameters.run_timeout_seconds === -1 && (
                <div className={styles.unlimitedNotice}>
                  <Sparkles size={15} />
                  <span>{t("threads.runTimeoutUnlimitedNotice")}</span>
                </div>
              )}
            </div>

            {/* Search Timeout */}
            <div className={styles.segmentedGroup}>
              <span>{t("threads.searchTimeoutLabel")}</span>
              <div className={styles.segmentedGrid}>
                {[
                  { label: "1m", val: 60 },
                  { label: "2m", val: 120 },
                  { label: "5m", val: 300 },
                  { label: "10m", val: 600 },
                ].map(({ label, val }) => (
                  <button
                    key={val}
                    type="button"
                    className={styles.segmentedGridButton}
                    data-active={parameters.search_timeout_seconds === val}
                    onClick={() => onChange({ search_timeout_seconds: val })}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <small className={styles.hint}>{t("threads.searchTimeoutHint")}</small>
            </div>

            {/* Posts with Comments limit & Min Replies */}
            {parameters.include_comments && (
              <>
                <div className={styles.segmentedGroup}>
                  <span>{t("threads.postsWithCommentsOption")}</span>
                  <div className={styles.segmentedControl}>
                    {[
                      { label: t("threads.postsWithCommentsAll"), val: -1 },
                      { label: "10", val: 10 },
                      { label: "25", val: 25 },
                      { label: "50", val: 50 },
                      { label: "100", val: 100 },
                    ].map(({ label, val }) => (
                      <button
                        key={val}
                        type="button"
                        className={styles.segmentedButton}
                        data-active={parameters.max_comment_posts === val}
                        onClick={() => onChange({ max_comment_posts: val })}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <small className={styles.hint}>{t("threads.maxCommentPostsHint")}</small>
                </div>

                <div className={styles.segmentedGroup}>
                  <span>{t("threads.minReplies")}</span>
                  <div className={styles.segmentedControl}>
                    {[
                      { label: "0", val: 0 },
                      { label: "≥ 2", val: 2 },
                      { label: "≥ 5", val: 5 },
                      { label: "≥ 10", val: 10 },
                    ].map(({ label, val }) => (
                      <button
                        key={val}
                        type="button"
                        className={styles.segmentedButton}
                        data-active={parameters.min_replies === val}
                        onClick={() => onChange({ min_replies: val })}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <small className={styles.hint}>{t("threads.minRepliesHint")}</small>
                </div>
              </>
            )}

            {/* Pacing Delays */}
            <div className={styles.segmentedGroup}>
              <span>{t("threads.delaysLabel")}</span>
              <div className={styles.segmentedControl}>
                <button
                  type="button"
                  className={styles.segmentedButton}
                  data-active={parameters.min_delay_seconds === 1 && parameters.max_delay_seconds === 2}
                  onClick={() => onChange({ min_delay_seconds: 1, max_delay_seconds: 2 })}
                >
                  {t("threads.delaysFast")}
                </button>
                <button
                  type="button"
                  className={styles.segmentedButton}
                  data-active={parameters.min_delay_seconds === 2 && parameters.max_delay_seconds === 4}
                  onClick={() => onChange({ min_delay_seconds: 2, max_delay_seconds: 4 })}
                >
                  {t("threads.delaysNormal")}
                </button>
                <button
                  type="button"
                  className={styles.segmentedButton}
                  data-active={parameters.min_delay_seconds === 4 && parameters.max_delay_seconds === 8}
                  onClick={() => onChange({ min_delay_seconds: 4, max_delay_seconds: 8 })}
                >
                  {t("threads.delaysSafe")}
                </button>
              </div>
              <small className={styles.hint}>{t("threads.delaysHint")}</small>
            </div>

            {/* Max Accounts */}
            <div className={styles.segmentedGroup}>
              <span>{t("threads.maxAccountsLabel")}</span>
              <div className={styles.segmentedControl}>
                {[
                  { label: `1 ${t("threads.accountUnit")}`, val: 1 },
                  { label: `2 ${t("threads.accountsUnit")}`, val: 2 },
                  { label: `3 ${t("threads.accountsUnit")}`, val: 3 },
                  { label: t("threads.maxAccountsAll"), val: -1 },
                ].map(({ label, val }) => (
                  <button
                    key={val}
                    type="button"
                    className={styles.segmentedButton}
                    data-active={parameters.max_accounts === val}
                    onClick={() => onChange({ max_accounts: val })}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <small className={styles.hint}>{t("threads.maxAccountsHint")}</small>
            </div>
          </div>
        )}
      </section>

      {expiredAccounts.length > 0 && (
        <div className={styles.notice} role="status" style={{ borderLeft: ready ? "4px solid #f59e0b" : "4px solid #ef4444" }}>
          <div className="flex items-start gap-2">
            <AlertTriangle className={`h-4 w-4 ${ready ? "text-amber-500" : "text-red-500"} shrink-0 mt-0.5`} />
            <div>
              <p style={{ margin: 0, fontWeight: 600, color: ready ? "#d97706" : "#ef4444" }}>
                {language === "vi" ? "Lưu ý phiên tài khoản" : "Session Notice"}
              </p>
              <p style={{ margin: "2px 0 8px 0", fontSize: "0.85rem" }}>
                {language === "vi"
                  ? ready
                    ? `Tài khoản (${expiredAccounts.map((a) => a.id).join(", ")}) có phiên đăng nhập đã hết hạn. Hệ thống sẽ tự động dùng các tài khoản đang hoạt động còn lại để cào dữ liệu.`
                    : `Tài khoản (${expiredAccounts.map((a) => a.id).join(", ")}) có phiên đăng nhập đã hết hạn. Vui lòng liên hệ Admin để cập nhật lại session JSON trong Cài đặt.`
                  : ready
                    ? `Session for account(s) ${expiredAccounts.map((a) => a.id).join(", ")} is expired. The system will automatically skip them and use the active accounts.`
                    : `Session for account(s) ${expiredAccounts.map((a) => a.id).join(", ")} has expired. Please ask an administrator to update the session JSON in Settings.`}
              </p>
              <Button variant="outline" size="sm" asChild className="gap-1.5 text-xs">
                <Link href="/settings/account">
                  <Settings size={13} />
                  {language === "vi" ? "Đi đến Cài đặt" : "Open Settings"}
                </Link>
              </Button>
            </div>
          </div>
        </div>
      )}

      {config && !ready && (
        <div className={styles.notice} role="status">
          <p style={{ margin: 0, marginBottom: "8px" }}>
            {language === "vi"
              ? "Thu thập Threads chưa có tài khoản nào sẵn sàng. Vui lòng liên hệ Admin cấu hình phiên trong Cài đặt."
              : "Threads collection needs setup. Ask an administrator to configure an account session in Settings."}
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link href="/settings/account">
                <Settings size={13} />
                {language === "vi" ? "Đi đến Cài đặt" : "Open Settings"}
              </Link>
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowImportModal(true)}
              className="gap-1.5 text-xs text-slate-500 hover:text-slate-700"
            >
              <KeyRound size={13} />
              Import Session JSON (Admin)
            </Button>
          </div>
        </div>
      )}

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <Button type="submit" className={styles.startButton} disabled={busy || !ready}>
        <Play size={15} />
        {busy
          ? t("threads.starting")
          : isQueuing
            ? (language === "vi" ? "Thêm vào hàng đợi" : "Add to queue")
            : t("threads.startCollection")}
      </Button>
      {isQueuing && (
        <p className={styles.queueHint} role="status">
          <Clock3 size={14} />
          <span>
            {language === "vi"
              ? "Đang có phiên khác đang chạy. Phiên mới sẽ được lưu vào danh sách chờ và tự động bắt đầu ngay sau khi phiên trước chạy xong."
              : "Another collection is currently running. This session will be queued and will automatically run once the previous one finishes."}
          </span>
        </p>
      )}
      <p className={styles.formFootnote}>Collections continue on the server after you close this page.</p>

      <ImportSessionModal
        open={showImportModal}
        onOpenChange={setShowImportModal}
        onSuccess={onRefreshConfig}
      />
    </form>
  );
}
