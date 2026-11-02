"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { z } from "zod";
import { ArrowDownToLine, ArrowRight, Check, ChevronDown, Clock3, Compass, LoaderCircle, MessagesSquare, Plus, SlidersHorizontal, X } from "lucide-react";

import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ThreadsApiError, threadsApi } from "./api";
import { DEFAULT_THREADS_PANELS, DEFAULT_THREADS_PARAMETERS, isActiveRun, loadThreadsPanels, loadThreadsSettings, saveThreadsPanels, saveThreadsSettings, type ThreadsPanels } from "./settings";
import { ThreadsForm } from "./threads-form";
import { ThreadsResults } from "./threads-results";
import { ThreadsHistory } from "./threads-history";
import { ThreadsSessionControls } from "./threads-session-controls";
import { ThreadsTravelForm } from "./threads-travel-form";
import { threadsConfigSchema, threadsParametersSchema, threadsRequestSchema, threadsRunSchema, type ThreadsConfig, type ThreadsParameters, type ThreadsRun } from "./types";
import styles from "./threads.module.css";

const STAGES = ["planning", "searching", "filtering", "comments", "curating", "saving"];
const STAGE_LABELS: Record<string, string> = {
  queued: "Waiting in queue", planning: "Planning the search", searching: "Collecting posts",
  filtering: "Filtering posts", comments: "Collecting comments", curating: "Analyzing results",
  saving: "Saving results", completed: "Collection complete", cancelled: "Collection cancelled", failed: "Collection failed",
};

function mergeRun(items: ThreadsRun[], run: ThreadsRun): ThreadsRun[] {
  return [{ ...run, result: null }, ...items.filter((item) => item.id !== run.id)]
    .sort((left, right) => right.created_at.localeCompare(left.created_at));
}

export function ThreadsWorkspace() {
  const pathname = usePathname();
  const { t, language } = useLanguage();
  const selectedId = pathname.startsWith("/tools/threads/") ? pathname.split("/")[3] : null;
  const [config, setConfig] = useState<ThreadsConfig | null>(null);
  const [parameters, setParameters] = useState<ThreadsParameters>(DEFAULT_THREADS_PARAMETERS);
  const [query, setQuery] = useState("");
  const [panels, setPanels] = useState<ThreadsPanels>(DEFAULT_THREADS_PANELS);
  const [history, setHistory] = useState<ThreadsRun[]>([]);
  const [runData, setRun] = useState<ThreadsRun | null>(null);
  const run = runData?.id === selectedId ? runData : null;
  const stages = run ? STAGES.filter((stage) =>
    (stage !== "filtering" || (run.request.pre_filter && run.request.pre_filter_strictness !== "none")) &&
    (stage !== "comments" || run.request.include_comments) &&
    (stage !== "curating" || run.request.curate)) : STAGES;
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [settingsNotice, setSettingsNotice] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [detailRevision, setDetailRevision] = useState(0);
  const [activeTab, setActiveTab] = useState<"scraper" | "travel">(() => {
    if (typeof window !== "undefined") {
      const saved = window.localStorage.getItem("cyverse.threads.activeTab");
      if (saved === "scraper" || saved === "travel") return saved;
    }
    return "scraper";
  });
  const deletingId = useRef<string | null>(null);
  const pendingKey = useRef<{ payload: string; key: string } | null>(null);
  const historyOffset = useRef(0);

  function getStageLabel(stage: string): string {
    const stageMap = t("threads.stages") as unknown as Record<string, string>;
    return stageMap?.[stage] ?? STAGE_LABELS[stage] ?? stage;
  }

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const [setup, items] = await Promise.all([
          threadsApi("/config", threadsConfigSchema, { signal: controller.signal }),
          threadsApi("/runs?limit=20", z.array(threadsRunSchema), { signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        const preferences = loadThreadsSettings(window.localStorage) ?? setup.defaults;
        const effective = setup.ai_available ? preferences : { ...preferences, expand_query: false, pre_filter: false, curate: false };
        setConfig(setup); setParameters(effective);
        setPanels(loadThreadsPanels(window.localStorage));
        setHistory((current) => [...items, ...current.filter((item) => !items.some((entry) => entry.id === item.id))]);
        setHasMore(items.length === 20); setError(null);
        historyOffset.current = items.length;
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not load Threads.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [retry]);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const item = await threadsApi(`/runs/${selectedId}`, threadsRunSchema, { signal: controller.signal });
        if (controller.signal.aborted) return;
        if (item.deletion_requested) deletingId.current = item.id;
        if (item.request.mode === "travel") {
          setActiveTab("travel");
        } else if (item.request.mode === "scraper") {
          setActiveTab("scraper");
        }
        setRun(item); setHistory((current) => mergeRun(current, item)); setDetailError(null);
        if (isActiveRun(item.status) || item.deletion_requested || item.archive_status !== "ready") {
          timer = setTimeout(poll, isActiveRun(item.status) || item.deletion_requested ? 2000 : 10000);
        }
      } catch (failure) {
        if (!controller.signal.aborted) {
          if (failure instanceof ThreadsApiError && failure.status === 404 && deletingId.current === selectedId) {
            setHistory((current) => current.filter((item) => item.id !== selectedId));
            setRun(null); setDetailError(null); deletingId.current = null;
            window.history.pushState(null, "", "/tools/threads");
            return;
          }
          setDetailError(failure instanceof Error ? failure.message : "Could not load this run.");
          timer = setTimeout(poll, 5000);
        }
      }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [selectedId, detailRevision]);

  const hasRunningSession = useMemo(
    () => history.some((item) => item.status === "running"),
    [history],
  );

  const runningRun = useMemo(
    () => history.find((item) => item.status === "running"),
    [history],
  );

  const queuedRuns = useMemo(
    () =>
      history
        .filter((item) => item.status === "queued")
        .sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [history],
  );

  const queuePosition = useMemo(() => {
    if (!run || run.status !== "queued") return 0;
    const index = queuedRuns.findIndex((item) => item.id === run.id);
    return index >= 0 ? index + 1 : 1;
  }, [run, queuedRuns]);

  const hasActiveRuns = useMemo(
    () => history.some((item) => isActiveRun(item.status)),
    [history],
  );

  useEffect(() => {
    if (!hasActiveRuns) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function pollQueue() {
      try {
        const items = await threadsApi("/runs?limit=20", z.array(threadsRunSchema), {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setHistory((current) => {
          const map = new Map(current.map((item) => [item.id, item]));
          for (const item of items) {
            const existing = map.get(item.id);
            if (existing) {
              map.set(item.id, { ...existing, ...item });
            } else {
              map.set(item.id, item);
            }
          }
          return Array.from(map.values()).sort((a, b) =>
            b.created_at.localeCompare(a.created_at),
          );
        });
      } catch {
        // Silently ignore background poll errors
      } finally {
        if (!controller.signal.aborted) {
          timer = setTimeout(pollQueue, 3000);
        }
      }
    }

    timer = setTimeout(pollQueue, 3000);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [hasActiveRuns]);

  function updatePanels(patch: Partial<ThreadsPanels>) {
    const next = { ...panels, ...patch };
    setPanels(next);
    saveThreadsPanels(window.localStorage, next);
  }

  function updateParameters(patch: Partial<ThreadsParameters>) {
    const next = { ...parameters, ...patch };
    setParameters(next);
    if (threadsParametersSchema.safeParse(next).success && !saveThreadsSettings(window.localStorage, next)) {
      setSettingsNotice("Browser preferences could not be saved. Your collection can still run.");
    }
  }

  function selectRun(id: string | null) {
    updatePanels({ settings_collapsed: id !== null });
    if (id === selectedId) return;
    setRun(null); setDetailError(null); setCancelling(false);
    window.history.pushState(null, "", id ? `/tools/threads/${id}` : "/tools/threads");
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validated = threadsRequestSchema.safeParse({ ...parameters, mode: "scraper", query, visibility: "public", keywords: [] });
    if (!validated.success) { setFormError(validated.error.issues[0]?.message ?? "Check your search settings."); return; }
    const payload = JSON.stringify(validated.data);
    if (pendingKey.current?.payload !== payload) pendingKey.current = { payload, key: crypto.randomUUID() };
    setCreating(true); setFormError(null);
    try {
      const item = await threadsApi("/runs", threadsRunSchema, {
        method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": pendingKey.current.key }, body: payload,
      });
      const savedParameters = threadsParametersSchema.parse(validated.data);
      setQuery(validated.data.query);
      saveThreadsSettings(window.localStorage, savedParameters);
      pendingKey.current = null;
      setHistory((current) => mergeRun(current, item)); selectRun(item.id); setRun(item);
    } catch (failure) {
      setFormError(failure instanceof Error ? failure.message : "Could not queue collection.");
    } finally { setCreating(false); }
  }

  async function submitTravel(travelPrompt: string, travelKeywords: string[]) {
    const validated = threadsRequestSchema.safeParse({
      ...parameters,
      mode: "travel",
      query: travelPrompt,
      keywords: travelKeywords,
      expand_query: false,
      check_duplicate: true,
      visibility: "public",
    });
    if (!validated.success) {
      setFormError(validated.error.issues[0]?.message ?? "Check your search settings.");
      return;
    }
    const payload = JSON.stringify(validated.data);
    const idempotencyKey = crypto.randomUUID();
    setCreating(true);
    setFormError(null);
    try {
      const item = await threadsApi("/runs", threadsRunSchema, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
        body: payload,
      });
      const savedParameters = threadsParametersSchema.parse(validated.data);
      saveThreadsSettings(window.localStorage, savedParameters);
      setHistory((current) => mergeRun(current, item));
      selectRun(item.id);
      setRun(item);
    } catch (failure) {
      setFormError(failure instanceof Error ? failure.message : "Could not queue collection.");
    } finally {
      setCreating(false);
    }
  }

  async function cancel() {
    if (!run) return;
    setCancelling(true); setDetailError(null);
    try {
      const item = await threadsApi(`/runs/${run.id}/cancel`, threadsRunSchema, { method: "POST" });
      setRun(item); setHistory((current) => mergeRun(current, item));
    } catch (failure) { setDetailError(failure instanceof Error ? failure.message : "Could not cancel collection."); }
    finally { setCancelling(false); }
  }

  async function loadMore() {
    setLoadingMore(true);
    try {
      const items = await threadsApi(`/runs?limit=20&offset=${historyOffset.current}`, z.array(threadsRunSchema));
      setHistory((current) => [...current, ...items.filter((item) => !current.some((entry) => entry.id === item.id))]);
      setHasMore(items.length === 20);
      historyOffset.current += items.length;
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not load history."); }
    finally { setLoadingMore(false); }
  }

  function updateRun(item: ThreadsRun) {
    if (item.deletion_requested) deletingId.current = item.id;
    setRun(item); setHistory((current) => mergeRun(current, item));
    setDetailRevision((value) => value + 1);
  }

  const tabHistory = useMemo(() => {
    return history.filter((item) => {
      const itemMode = item.request.mode ?? "scraper";
      return activeTab === "travel" ? itemMode === "travel" : itemMode !== "travel";
    });
  }, [history, activeTab]);

  return (
    <main className={styles.workspace}>
      {/* ChatGPT-Style Segmented Pill Toggle centered at the top */}
      <div className={styles.topTabBar}>
        <div className={styles.chatGptSegmentedToggle} role="tablist" aria-label="Chế độ làm việc Threads">
          <button
            type="button"
            role="tab"
            id="tab-threads-scraper"
            aria-selected={activeTab === "scraper"}
            aria-controls="panel-threads-scraper"
            className={`${styles.chatGptTab} ${activeTab === "scraper" ? styles.chatGptTabActive : ""}`}
            onClick={() => {
              setActiveTab("scraper");
              if (typeof window !== "undefined") {
                window.localStorage.setItem("cyverse.threads.activeTab", "scraper");
              }
              if (run && (run.request.mode ?? "scraper") === "travel") {
                selectRun(null);
              }
            }}
          >
            <span>{t("threads.tabScraper")}</span>
          </button>
          <button
            type="button"
            role="tab"
            id="tab-threads-travel"
            aria-selected={activeTab === "travel"}
            aria-controls="panel-threads-travel"
            className={`${styles.chatGptTab} ${activeTab === "travel" ? styles.chatGptTabActive : ""}`}
            onClick={() => {
              setActiveTab("travel");
              if (typeof window !== "undefined") {
                window.localStorage.setItem("cyverse.threads.activeTab", "travel");
              }
              if (run && (run.request.mode ?? "scraper") !== "travel") {
                selectRun(null);
              }
            }}
          >
            <span>{t("threads.tabTravel")}</span>
          </button>
        </div>
      </div>

      <div id="panel-threads-workspace" role="tabpanel">
        <header className={styles.heading}>
          <div>
            <p className={styles.eyebrow}>
              {activeTab === "travel" ? <Compass size={15} /> : <MessagesSquare size={15} />}
              {activeTab === "travel" ? t("threads.travelEyebrow") : t("threads.eyebrow")}
            </p>
            <h1>{activeTab === "travel" ? t("threads.travelHeading") : t("threads.heading")}</h1>
            <p>{activeTab === "travel" ? t("threads.travelSubheading") : t("threads.subheading")}</p>
          </div>
        </header>
        {error && (
          <div className={styles.error} role="alert">
            {error}
            <button
              type="button"
              onClick={() => {
                setLoading(true);
                setRetry((value) => value + 1);
              }}
            >
              Retry
            </button>
          </div>
        )}
        {settingsNotice && (
          <p className={styles.notice} role="status">
            {settingsNotice}
          </p>
        )}
        {config && !config.cloudinary_ready && (
          <p className={styles.notice}>
            Cloudinary is not configured. Collections are saved in the database and TXT downloads
            are available. Cloud archiving will retry after configuration.
          </p>
        )}
        <div className={styles.layout} data-history-collapsed={panels.history_collapsed}>
          <ThreadsHistory
            items={tabHistory}
            selectedId={selectedId}
            collapsed={panels.history_collapsed}
            loading={loading}
            loadingMore={loadingMore}
            hasMore={hasMore}
            title={
              activeTab === "travel"
                ? language === "vi"
                  ? "Lịch sử địa điểm"
                  : "Travel history"
                : t("threads.historyHeading")
            }
            emptyHint={
              activeTab === "travel"
                ? language === "vi"
                  ? "Chưa có phiên cào địa điểm du lịch nào."
                  : "No travel collections yet."
                : t("threads.emptyHistoryHint")
            }
            onToggle={() => updatePanels({ history_collapsed: !panels.history_collapsed })}
            onSelect={selectRun}
            onNew={() => selectRun(null)}
            onLoadMore={loadMore}
          />
          <div className={styles.content}>
            <section className={styles.controls} aria-label="Search settings">
              <button
                type="button"
                className={styles.settingsToggle}
                aria-label={
                  panels.settings_collapsed
                    ? "Expand search settings"
                    : "Collapse search settings"
                }
                aria-expanded={!panels.settings_collapsed}
                aria-controls="threads-settings-content"
                onClick={() =>
                  updatePanels({ settings_collapsed: !panels.settings_collapsed })
                }
              >
                <span>
                  <SlidersHorizontal size={17} />
                  {activeTab === "travel"
                    ? "Cấu hình tìm kiếm Du lịch & Địa điểm"
                    : "Search settings"}
                </span>
                <span
                  className={styles.settingsToggleChevron}
                  data-collapsed={panels.settings_collapsed}
                >
                  <ChevronDown size={17} />
                </span>
              </button>
              <div
                id="threads-settings-content"
                className={styles.settingsAccordion}
                data-collapsed={panels.settings_collapsed}
              >
                <div className={styles.settingsAccordionInner}>
                  {activeTab === "travel" ? (
                    <ThreadsTravelForm
                      config={config}
                      parameters={parameters}
                      busy={creating || loading}
                      error={formError}
                      isQueuing={hasRunningSession}
                      onChange={updateParameters}
                      onReset={() => {
                        const defaults = config?.defaults ?? DEFAULT_THREADS_PARAMETERS;
                        updateParameters({
                          ...defaults,
                          mode: "travel",
                          search_type: "both",
                          expand_query: false,
                          check_duplicate: true,
                        });
                        setFormError(null);
                      }}
                      onSubmit={submitTravel}
                      onRefreshConfig={() => setRetry((c) => c + 1)}
                    />
                  ) : (
                    <ThreadsForm
                      config={config}
                      parameters={parameters}
                      query={query}
                      busy={creating || loading}
                      error={formError}
                      isQueuing={hasRunningSession}
                      onQuery={setQuery}
                      onChange={updateParameters}
                      onSubmit={submit}
                      onRefreshConfig={() => setRetry((c) => c + 1)}
                      onReset={() => {
                        const defaults = config?.defaults ?? DEFAULT_THREADS_PARAMETERS;
                        updateParameters(
                          config?.ai_available
                            ? defaults
                            : { ...defaults, expand_query: false, pre_filter: false, curate: false }
                        );
                        setFormError(null);
                      }}
                    />
                  )}
                </div>
              </div>
            </section>
              <section className={styles.collectionPanel} aria-label="Selected collection">
                {detailError && (
                  <p className={styles.error} role="alert">
                    {detailError}
                  </p>
                )}
                {selectedId && !run && !detailError && (
                  <div className={styles.empty} role="status">
                    <LoaderCircle className={styles.spinner} />
                    <p>{t("threads.loading")}</p>
                  </div>
                )}
                {!selectedId && (
                  <div className={styles.welcome}>
                    <div className={styles.welcomeIcon}>
                      {activeTab === "travel" ? <Compass size={35} /> : <MessagesSquare size={35} />}
                    </div>
                    <p className={styles.eyebrow}>
                      {activeTab === "travel" ? t("threads.travelEyebrow") : t("threads.fromConversationToContext")}
                    </p>
                    <h2>
                      {activeTab === "travel"
                        ? "Khám phá địa điểm du lịch & quán ngon."
                        : t("threads.welcomeHeading")}
                    </h2>
                    <p>
                      {activeTab === "travel"
                        ? "Nhập prompt du lịch, AI sẽ phân tích từ khóa theo nhóm để tối ưu tìm kiếm và tự động lọc trùng lặp khi cào."
                        : t("threads.welcomeSubtitle")}
                    </p>
                    <div className={styles.steps}>
                      <span>
                        <b>01</b>
                        {activeTab === "travel" ? "Nhập Prompt & Phân tích" : t("threads.step1")}
                      </span>
                      <ArrowRight size={15} />
                      <span>
                        <b>02</b>
                        {activeTab === "travel" ? "Tùy chỉnh nhóm từ khóa" : t("threads.step2")}
                      </span>
                      <ArrowRight size={15} />
                      <span>
                        <b>03</b>
                        {activeTab === "travel" ? "Thu thập & Lọc trùng" : t("threads.step3")}
                      </span>
                    </div>
                  </div>
                )}
                {run && (
                  <>
                    <div className={styles.runHeading}>
                      <div>
                        <Badge
                          variant={
                            run.status === "failed"
                              ? "destructive"
                              : run.status === "completed"
                                ? "success"
                                : run.status === "queued"
                                  ? "warning"
                                  : run.status === "running"
                                    ? "default"
                                    : "secondary"
                          }
                        >
                          {run.deletion_requested
                            ? language === "vi"
                              ? "Đang xóa"
                              : "Deleting"
                            : run.status === "queued"
                              ? language === "vi"
                                ? "Đang chờ trong hàng đợi"
                                : "Queued in line"
                              : run.status === "running"
                                ? language === "vi"
                                  ? "Đang chạy"
                                  : "Running"
                                : run.status === "completed"
                                  ? language === "vi"
                                    ? "Hoàn tất"
                                    : "Completed"
                                  : run.status === "failed"
                                    ? language === "vi"
                                      ? "Thất bại"
                                      : "Failed"
                                    : run.status}
                        </Badge>
                        <h2>{run.request.query}</h2>
                        <p>
                          {new Date(run.created_at).toLocaleString(
                            language === "vi" ? "vi-VN" : "en",
                            { dateStyle: "medium", timeStyle: "short" }
                          )}
                        </p>
                      </div>
                    </div>
                    <ThreadsSessionControls key={run.id} run={run} onUpdated={updateRun} />
                    {run.status === "queued" && (
                      <div className={styles.queuePanel} role="status" aria-live="polite">
                        <div className={styles.queuePanelHeader}>
                          <Clock3 size={20} className={styles.queuePanelIcon} />
                          <div>
                            <div className={styles.queuePanelTitle}>
                              <span>
                                {language === "vi"
                                  ? `Đang chờ trong hàng đợi (Thứ tự #${queuePosition > 0 ? queuePosition : 1})`
                                  : `Queued in collection list (Position #${queuePosition > 0 ? queuePosition : 1})`}
                              </span>
                              <Badge variant="warning">
                                {language === "vi" ? "Chờ chạy" : "Queued"}
                              </Badge>
                            </div>
                            <p className={styles.queuePanelDescription}>
                              {runningRun && runningRun.id !== run.id
                                ? language === "vi"
                                  ? `Hệ thống đang cào phiên "${runningRun.request.query}". Phiên này đã được lưu trước vào danh sách và sẽ tự động bắt đầu ngay sau khi phiên trước chạy xong.`
                                  : `Collection "${runningRun.request.query}" is currently running. This session is saved and will automatically start crawling once the current one finishes.`
                                : language === "vi"
                                  ? "Phiên này đã được lưu vào hệ thống và đang chờ worker khởi động thu thập."
                                  : "This session is queued and waiting for worker execution to start."}
                            </p>
                          </div>
                        </div>
                        <div className={styles.queuePanelActions}>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              selectRun(null);
                              updatePanels({ settings_collapsed: false });
                            }}
                          >
                            <Plus size={14} />
                            {language === "vi" ? "Tạo thêm phiên cào khác" : "Queue another collection"}
                          </Button>
                          {run.can_manage && (
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={cancelling || run.deletion_requested}
                              onClick={cancel}
                            >
                              <X size={14} />
                              {cancelling
                                ? t("threads.cancelling")
                                : language === "vi"
                                  ? "Hủy phiên chờ này"
                                  : "Cancel queued session"}
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                    {run.status === "running" && (
                      <div
                        className={styles.progressPanel}
                        role="status"
                        aria-live="polite"
                      >
                        <div>
                          <LoaderCircle size={16} className={styles.spinner} />
                          <strong>{getStageLabel(run.stage)}</strong>
                          <span>{Math.round(run.progress * 100)}%</span>
                        </div>
                        <progress value={run.progress} max={1} aria-label="Collection progress" />
                        <p>{t("threads.backgroundNotice")}</p>
                        {run.can_manage && (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={cancelling || run.deletion_requested}
                            onClick={cancel}
                          >
                            <X size={14} />
                            {cancelling ? t("threads.cancelling") : t("threads.cancelCollection")}
                          </Button>
                        )}
                      </div>
                    )}
                    {run.status === "failed" && (
                      <p className={styles.error} role="alert">
                        {run.error_message ?? t("threads.failedNotice")}
                      </p>
                    )}
                    {run.status === "cancelled" && (
                      <p className={styles.notice}>
                        This collection was cancelled. Start a new collection to try again.
                      </p>
                    )}
                    <ol className={styles.stageList} aria-label="Collection stages">
                      {stages.map((stage, index) => {
                        const done =
                          run.status === "completed" ||
                          (isActiveRun(run.status) && stages.indexOf(run.stage) > index);
                        return (
                          <li key={stage} data-active={stage === run.stage} data-done={done}>
                            {done ? <Check size={11} /> : <span>{index + 1}</span>}
                            {getStageLabel(stage)}
                          </li>
                        );
                      })}
                    </ol>
                    {run.result && !run.deletion_requested && (
                      <>
                        {isActiveRun(run.status) ? (
                          <p className={styles.notice}>
                            {language === "vi"
                              ? "Hệ thống đang tự động lưu dữ liệu sau mỗi từ khóa. Tính năng xuất file (JSON / TXT) sẽ sẵn sàng ngay khi phiên cào hoàn tất hoặc dừng."
                              : "Posts are automatically saved to the database after each keyword. File exports (JSON / TXT) will unlock once the collection finishes or stops."}
                          </p>
                        ) : run.status === "cancelled" ? (
                          <p className={styles.notice}>
                            {language === "vi"
                              ? "Phiên cào đã được hủy. Quá trình thu thập đã dừng và toàn bộ dữ liệu đã được xóa sạch."
                              : "The collection session was cancelled. The process has been stopped and all data was wiped clean."}
                          </p>
                        ) : run.status !== "completed" ? (
                          <p className={styles.notice}>
                            {language === "vi"
                              ? `Phiên chạy đã dừng (${run.status}). Đã lưu và tổng hợp ${run.result.posts.length} bài viết thu được để bạn có thể xuất file.`
                              : `Collection stopped (${run.status}). Synthesized ${run.result.posts.length} posts saved before stopping, ready for export below.`}
                          </p>
                        ) : null}
                        {!isActiveRun(run.status) && run.status !== "cancelled" && run.result.posts.length > 0 && (
                          <div className={styles.exportBar}>
                            <h3>
                              {t("threads.collectionResults")} ({run.result.posts.length}{" "}
                              {language === "vi" ? "bài viết" : "posts"})
                            </h3>
                            <div className={styles.exportButtons}>
                              <a
                                href={`/api/threads/runs/${run.id}/export?format=json`}
                                download
                                className={styles.exportActionBtn}
                              >
                                <ArrowDownToLine size={14} />
                                {t("threads.exportJson")}
                              </a>
                              <a
                                href={`/api/threads/runs/${run.id}/export?format=txt`}
                                download
                                className={styles.exportActionBtn}
                              >
                                <ArrowDownToLine size={14} />
                                {t("threads.exportTxt")}
                              </a>
                            </div>
                          </div>
                        )}
                        {run.status !== "cancelled" && <ThreadsResults key={run.id} run={run} />}
                      </>
                    )}
                  </>
                )}
              </section>
            </div>
          </div>
        </div>
    </main>
  );
}
