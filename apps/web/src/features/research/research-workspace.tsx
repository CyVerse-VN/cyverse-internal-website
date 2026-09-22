"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  MoreHorizontal,
  Pencil,
  RotateCcw,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import {
  EMPTY_PAPER_FILTERS,
  facetCounts,
  filterAndSortPapers,
  type PaperFilters,
} from "./filters";
import {
  FALLBACK_RESEARCH_CONFIG,
  defaultPreferences,
  loadPreferences,
  savePreferences,
  timeRangeOptions,
  toResearchSettings,
  type ResearchPreferences,
} from "./settings";
import {
  ACTIVE_RESEARCH_STATUSES,
  type ResearchConfig,
  type ResearchOwner,
  type ResearchSessionDetail,
  type ResearchSessionList,
  type ResearchSessionSummary,
  type ResearchSource,
  type ResearchVisibility,
} from "./types";

const SOURCE_LABELS: Record<ResearchSource, string> = {
  semantic_scholar: "Semantic Scholar",
  arxiv: "arXiv",
  openalex: "OpenAlex",
};

class ResearchApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = "The request could not be completed.";
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Keep the safe fallback for malformed upstream responses.
    }
    throw new ResearchApiError(message, response.status);
  }
  return (await response.json()) as T;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(
    new Date(value),
  );
}

function formatPaperDate(
  publishedAt: string | null | undefined,
  year: number | null | undefined,
): string {
  if (publishedAt) {
    const trimmed = publishedAt.trim();
    const datePart = trimmed.split("T")[0];
    const parts = datePart.split("-");
    if (parts.length === 3 && parts[0].length === 4) {
      const [y, m, d] = parts;
      return `${d.padStart(2, "0")}/${m.padStart(2, "0")}/${y}`;
    }
    if (parts.length === 2 && parts[0].length === 4) {
      const [y, m] = parts;
      return `01/${m.padStart(2, "0")}/${y}`;
    }
    const parsed = new Date(trimmed);
    if (!isNaN(parsed.getTime())) {
      const d = String(parsed.getDate()).padStart(2, "0");
      const m = String(parsed.getMonth() + 1).padStart(2, "0");
      const y = parsed.getFullYear();
      return `${d}/${m}/${y}`;
    }
  }
  if (year) {
    return `01/01/${year}`;
  }
  return "Unknown date";
}

function sessionTone(status: string): string {
  if (status === "completed") return "success";
  if (status === "completed_with_warnings") return "warning";
  if (status === "failed" || status === "cancelled") return "danger";
  return "active";
}

function upsertSession(
  sessions: ResearchSessionSummary[],
  session: ResearchSessionSummary,
): ResearchSessionSummary[] {
  return [session, ...sessions.filter((item) => item.id !== session.id)].sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  );
}

export function ResearchWorkspace({ initialSessionId }: { initialSessionId: string | null }) {
  const [config, setConfig] = useState<ResearchConfig>(FALLBACK_RESEARCH_CONFIG);
  const [preferences, setPreferences] = useState<ResearchPreferences>(() =>
    defaultPreferences(FALLBACK_RESEARCH_CONFIG),
  );
  const [query, setQuery] = useState("");
  const [visibility, setVisibility] = useState<ResearchVisibility>("public");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(initialSessionId ?? null);
  const [selected, setSelected] = useState<ResearchSessionDetail | null>(null);
  const [filters, setFilters] = useState<PaperFilters>(EMPTY_PAPER_FILTERS);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingSession, setLoadingSession] = useState(Boolean(initialSessionId));
  const [submitting, setSubmitting] = useState(false);
  const [sessionActionId, setSessionActionId] = useState<string | null>(null);
  const [sessionToDelete, setSessionToDelete] = useState<ResearchSessionSummary | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameSaving, setRenameSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sessionCacheRef = useRef<Map<string, ResearchSessionDetail>>(new Map());
  const activeSessionRequestRef = useRef<AbortController | null>(null);
  const deletedSessionIdsRef = useRef<Set<string>>(new Set());
  const editingSessionRef = useRef<ResearchSessionSummary | null>(null);
  const renameFormRef = useRef<HTMLFormElement | null>(null);
  const renameValueRef = useRef(renameValue);
  useEffect(() => {
    renameValueRef.current = renameValue;
  }, [renameValue]);

  useEffect(() => {
    return () => {
      activeSessionRequestRef.current?.abort();
    };
  }, []);

  const requestHistory = useCallback(async (cursor?: string) => {
    const suffix = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
    return readJson<ResearchSessionList>(await fetch(`/api/research/sessions${suffix}`));
  }, []);

  const fetchHistory = useCallback(async (cursor?: string) => {
    const data = await requestHistory(cursor);
    const filterDeleted = (items: ResearchSessionSummary[]) =>
      items.filter((item) => !deletedSessionIdsRef.current.has(item.id));
    setSessions((current) => (cursor ? [...current, ...filterDeleted(data.items)] : filterDeleted(data.items)));
    setNextCursor(data.next_cursor);
  }, [requestHistory]);

  const requestSession = useCallback(async (sessionId: string, signal?: AbortSignal) => {
    return readJson<ResearchSessionDetail>(
      await fetch(`/api/research/sessions/${encodeURIComponent(sessionId)}`, {
        cache: "no-store",
        signal,
      }),
    );
  }, []);

  const fetchSession = useCallback(async (sessionId: string, signal?: AbortSignal) => {
    const data = await requestSession(sessionId, signal);
    sessionCacheRef.current.set(data.id, data);
    setSelected(data);
    setVisibility(data.visibility);
    setSessions((current) => upsertSession(current, data));
    return data;
  }, [requestSession]);

  const selectSession = useCallback(
    async (sessionId: string, pushToHistory = true) => {
      if (activeId === sessionId && selected?.id === sessionId) return;

      activeSessionRequestRef.current?.abort();

      if (pushToHistory) {
        window.history.pushState(null, "", `/tools/research/${sessionId}`);
      }

      setActiveId(sessionId);
      // Immediately reset selected to prevent old papers/content from displaying
      setSelected(null);
      setError(null);

      const cached = sessionCacheRef.current.get(sessionId);
      if (cached) {
        setSelected(cached);
        setVisibility(cached.visibility);
        setLoadingSession(false);
        return;
      }

      setLoadingSession(true);
      const controller = new AbortController();
      activeSessionRequestRef.current = controller;

      try {
        const data = await requestSession(sessionId, controller.signal);
        if (controller.signal.aborted) return;
        sessionCacheRef.current.set(sessionId, data);
        setSelected(data);
        setVisibility(data.visibility);
        setSessions((current) => upsertSession(current, data));
      } catch (caught) {
        if (controller.signal.aborted) return;
        setError(caught instanceof Error ? caught.message : "Unable to load this session.");
      } finally {
        if (!controller.signal.aborted) {
          setLoadingSession(false);
        }
      }
    },
    [activeId, selected?.id, requestSession],
  );

  const startNewSession = useCallback(() => {
    activeSessionRequestRef.current?.abort();
    window.history.pushState(null, "", "/tools/research");
    setActiveId(null);
    setSelected(null);
    setVisibility(config.default_visibility);
    setError(null);
    setLoadingSession(false);
  }, [config.default_visibility]);

  useEffect(() => {
    let active = true;
    void Promise.all([
      fetch("/api/research/config", { cache: "no-store" })
        .then((response) => readJson<ResearchConfig>(response))
        .catch(() => FALLBACK_RESEARCH_CONFIG),
      requestHistory(),
    ]).then(([loadedConfig, history]) => {
      if (!active) return;
      setConfig(loadedConfig);
      setPreferences(loadPreferences(loadedConfig));
      setVisibility(loadedConfig.default_visibility);
      setSessions(history.items.filter((item) => !deletedSessionIdsRef.current.has(item.id)));
      setNextCursor(history.next_cursor);
      setLoadingHistory(false);
    }).catch((caught: unknown) => {
      if (!active) return;
      setError(caught instanceof Error ? caught.message : "Unable to load research.");
      setLoadingHistory(false);
    });
    return () => {
      active = false;
    };
  }, [requestHistory]);

  useEffect(() => {
    if (!initialSessionId) return;
    const controller = new AbortController();
    void requestSession(initialSessionId, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        sessionCacheRef.current.set(data.id, data);
        setSelected(data);
        setVisibility(data.visibility);
        setSessions((current) => upsertSession(current, data));
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) {
          setError(caught instanceof Error ? caught.message : "Unable to load this session.");
          setSelected(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingSession(false);
      });
    return () => controller.abort();
  }, [initialSessionId, requestSession]);

  useEffect(() => {
    const handlePopState = () => {
      const pathname = window.location.pathname;
      const match = pathname.match(/\/tools\/research\/([^/]+)/);
      if (match && match[1]) {
        setActiveId(match[1]);
        void selectSession(match[1], false);
      } else {
        activeSessionRequestRef.current?.abort();
        setActiveId(null);
        setSelected(null);
        setVisibility(config.default_visibility);
        setLoadingSession(false);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [selectSession, config.default_visibility]);

  const activeSessionId = selected?.id;
  const activeSessionStatus = selected?.status;
  useEffect(() => {
    if (!activeSessionId || !activeSessionStatus || !ACTIVE_RESEARCH_STATUSES.has(activeSessionStatus) || activeSessionId.startsWith("temp-")) {
      return;
    }
    let stopped = false;
    let inFlight = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();
    const poll = async () => {
      if (inFlight || stopped) return;
      inFlight = true;
      try {
        const latest = await fetchSession(activeSessionId, controller.signal);
        if (!ACTIVE_RESEARCH_STATUSES.has(latest.status)) return;
      } catch (caught) {
        if (!controller.signal.aborted) {
          if (caught instanceof ResearchApiError && [403, 404].includes(caught.status)) {
            sessionCacheRef.current.delete(activeSessionId);
            setSessions((current) => current.filter((item) => item.id !== activeSessionId));
            setSelected(null);
            window.history.replaceState(null, "", "/tools/research");
            setError("This research session is no longer available to you.");
            return;
          }
          setError(caught instanceof Error ? caught.message : "Progress could not be refreshed.");
        }
      } finally {
        inFlight = false;
      }
      if (!stopped) timer = setTimeout(poll, document.hidden ? 5000 : 2000);
    };
    timer = setTimeout(poll, 2000);
    const handleFocus = () => {
      if (!document.hidden && !stopped) {
        if (timer) clearTimeout(timer);
        timer = undefined;
        void poll();
      }
    };
    document.addEventListener("visibilitychange", handleFocus);
    return () => {
      stopped = true;
      controller.abort();
      if (timer) clearTimeout(timer);
      document.removeEventListener("visibilitychange", handleFocus);
    };
  }, [activeSessionId, activeSessionStatus, fetchSession]);

  async function submitSearch(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const normalized = query.trim().replace(/\s+/g, " ");
    if (normalized.length < config.limits.query_min) {
      setError(`Enter at least ${config.limits.query_min} characters.`);
      return;
    }
    if (normalized.length > config.limits.query_max) {
      setError(`Use no more than ${config.limits.query_max} characters.`);
      return;
    }
    if (preferences.sources.length === 0) {
      setError("Select at least one source.");
      return;
    }
    const requestSettings = toResearchSettings(config, preferences);
    const minYear = Math.max(config.limits.year_min, 2020);
    if (
      preferences.timeRange === "custom" &&
      (requestSettings.year_from === null ||
        requestSettings.year_to === null ||
        requestSettings.year_from < minYear ||
        requestSettings.year_to > config.limits.year_max ||
        requestSettings.year_from > requestSettings.year_to)
    ) {
      setError(
        `Enter a valid year range from ${minYear} to ${config.limits.year_max}.`,
      );
      return;
    }
    setSubmitting(true);
    setError(null);

    // Optimistic creation: Add session immediately on FE
    const tempId = `temp-${crypto.randomUUID()}`;
    const ownerInfo: ResearchOwner = sessions.find((s) => s.can_manage)?.owner ?? {
      id: "current-user",
      display_name: "You",
    };
    const nowIso = new Date().toISOString();
    const optimisticSession: ResearchSessionDetail = {
      id: tempId,
      query: normalized,
      title: normalized,
      visibility,
      owner: ownerInfo,
      is_owner: true,
      can_manage: true,
      status: "queued",
      current_stage: "queued",
      progress: 0,
      queue_position: 1,
      result_count: 0,
      created_at: nowIso,
      updated_at: nowIso,
      effective_settings: requestSettings,
      pipeline_version: "v1",
      warnings: [],
      result_stats: {},
      error: null,
      events: [],
      papers: [],
    };

    setActiveId(tempId);
    setSessions((current) => [optimisticSession, ...current.filter((item) => item.id !== tempId)]);
    sessionCacheRef.current.set(tempId, optimisticSession);
    setSelected(optimisticSession);
    window.history.pushState(null, "", `/tools/research/${tempId}`);
    setQuery("");

    try {
      const created = await readJson<ResearchSessionDetail>(
        await fetch("/api/research/sessions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": crypto.randomUUID(),
          },
          body: JSON.stringify({
            query: normalized,
            visibility,
            settings: requestSettings,
          }),
        }),
      );
      sessionCacheRef.current.delete(tempId);
      sessionCacheRef.current.set(created.id, created);
      setActiveId(created.id);
      setSessions((current) => [created, ...current.filter((item) => item.id !== tempId && item.id !== created.id)]);
      setSelected((current) => (current?.id === tempId ? created : current));
      window.history.replaceState(null, "", `/tools/research/${created.id}`);
    } catch (caught) {
      sessionCacheRef.current.delete(tempId);
      setActiveId((current) => (current === tempId ? null : current));
      setSessions((current) => current.filter((item) => item.id !== tempId));
      setSelected((current) => (current?.id === tempId ? null : current));
      window.history.replaceState(null, "", "/tools/research");
      setError(caught instanceof Error ? caught.message : "Unable to start the search.");
    } finally {
      setSubmitting(false);
    }
  }

  async function cancelSelected(): Promise<void> {
    if (!selected || selected.id.startsWith("temp-")) return;
    setError(null);
    try {
      const updated = await readJson<ResearchSessionDetail>(
        await fetch(`/api/research/sessions/${selected.id}/cancel`, { method: "POST" }),
      );
      sessionCacheRef.current.set(updated.id, updated);
      setSelected(updated);
      setSessions((current) => upsertSession(current, updated));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to cancel this session.");
    }
  }

  async function changeVisibility(next: ResearchVisibility): Promise<void> {
    if (!selected || selected.id.startsWith("temp-")) return;
    if (selected.visibility === next) return;

    const previousSelected = selected;
    const optimistic: ResearchSessionDetail = { ...selected, visibility: next };
    setSelected(optimistic);
    setVisibility(next);
    sessionCacheRef.current.set(selected.id, optimistic);
    setSessions((current) => upsertSession(current, optimistic));
    setError(null);

    try {
      const updated = await readJson<ResearchSessionDetail>(
        await fetch(`/api/research/sessions/${selected.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ visibility: next }),
        }),
      );
      sessionCacheRef.current.set(updated.id, updated);
      setSelected(updated);
      setVisibility(updated.visibility);
      setSessions((current) => upsertSession(current, updated));
    } catch (caught) {
      sessionCacheRef.current.set(previousSelected.id, previousSelected);
      setSelected(previousSelected);
      setVisibility(previousSelected.visibility);
      setSessions((current) => upsertSession(current, previousSelected));
      setError(caught instanceof Error ? caught.message : "Unable to update visibility.");
    }
  }

  function startRename(session: ResearchSessionSummary): void {
    editingSessionRef.current = session;
    setEditingSessionId(session.id);
    setRenameValue(session.title);
  }

  const cancelRename = useCallback((): void => {
    if (renameSaving) return;
    editingSessionRef.current = null;
    setEditingSessionId(null);
    setRenameValue("");
  }, [renameSaving]);

  const handleRenameSubmit = useCallback(
    async (session: ResearchSessionSummary, valueOverride?: string): Promise<void> => {
      const rawTitle = valueOverride !== undefined ? valueOverride : renameValueRef.current;
      const title = rawTitle.trim().replace(/\s+/g, " ");
      if (!title || title.length > 120) {
        if (valueOverride !== undefined) {
          cancelRename();
          return;
        }
        setError("Session name must contain between 1 and 120 characters.");
        return;
      }
      if (title === session.title) {
        editingSessionRef.current = null;
        setEditingSessionId(null);
        return;
      }
      setRenameSaving(true);
      setSessionActionId(session.id);
      setError(null);
      try {
        const updated = await readJson<ResearchSessionDetail>(
          await fetch(`/api/research/sessions/${session.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title }),
          }),
        );
        sessionCacheRef.current.set(updated.id, updated);
        setSessions((current) => upsertSession(current, updated));
        setSelected((current) => (current?.id === updated.id ? updated : current));
        editingSessionRef.current = null;
        setEditingSessionId(null);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to rename this session.");
      } finally {
        setRenameSaving(false);
        setSessionActionId(null);
      }
    },
    [cancelRename],
  );

  useEffect(() => {
    if (!editingSessionId) return;

    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null;
      if (renameFormRef.current && target && !renameFormRef.current.contains(target)) {
        const active = editingSessionRef.current;
        if (active) {
          const trimmed = renameValueRef.current.trim().replace(/\s+/g, " ");
          if (trimmed && trimmed.length <= 120 && trimmed !== active.title) {
            void handleRenameSubmit(active, trimmed);
          } else {
            cancelRename();
          }
        } else {
          cancelRename();
        }
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
    };
  }, [editingSessionId, handleRenameSubmit, cancelRename]);

  async function confirmDeleteSession(): Promise<void> {
    if (!sessionToDelete) return;
    const session = sessionToDelete;
    const targetId = session.id;
    const cachedDetail = sessionCacheRef.current.get(targetId);
    const wasSelected = selected?.id === targetId;
    const previousSelected = selected;

    // Immediately close modal and remove session from UI (optimistic delete)
    setSessionToDelete(null);
    setError(null);
    if (editingSessionId === targetId) {
      setEditingSessionId(null);
    }
    deletedSessionIdsRef.current.add(targetId);
    sessionCacheRef.current.delete(targetId);
    setSessions((current) => current.filter((item) => item.id !== targetId));
    if (wasSelected) {
      setActiveId(null);
      setSelected(null);
      window.history.replaceState(null, "", "/tools/research");
    }

    try {
      const response = await fetch(`/api/research/sessions/${targetId}`, {
        method: "DELETE",
      });
      if (!response.ok) await readJson<never>(response);
    } catch (caught) {
      // Revert optimistic deletion if the API call fails
      deletedSessionIdsRef.current.delete(targetId);
      setSessions((current) => {
        if (current.some((item) => item.id === targetId)) return current;
        return [session, ...current];
      });
      if (cachedDetail) {
        sessionCacheRef.current.set(targetId, cachedDetail);
      }
      if (wasSelected) {
        setActiveId(targetId);
        setSelected((current) => (current === null ? previousSelected : current));
      }
      setError(caught instanceof Error ? caught.message : "Unable to delete this session.");
    }
  }

  function updatePreference<K extends keyof ResearchPreferences>(
    key: K,
    value: ResearchPreferences[K],
  ): void {
    const next = { ...preferences, [key]: value };
    savePreferences(config, next);
    setPreferences(next);
  }

  function resetPreferences(): void {
    const next = defaultPreferences(config);
    savePreferences(config, next);
    setPreferences(next);
  }

  function toggleSource(source: ResearchSource): void {
    const enabled = preferences.sources.includes(source);
    if (enabled && preferences.sources.length === 1) return;
    updatePreference(
      "sources",
      enabled
        ? preferences.sources.filter((value) => value !== source)
        : [...preferences.sources, source],
    );
  }

  const papers = useMemo(
    () => filterAndSortPapers(selected?.papers ?? [], filters),
    [filters, selected?.papers],
  );
  const yearCounts = useMemo(() => facetCounts(selected?.papers ?? [], "year"), [selected?.papers]);
  const typeCounts = useMemo(
    () => facetCounts(selected?.papers ?? [], "paper_type"),
    [selected?.papers],
  );
  const sourceOptions = useMemo(
    () => Array.from(new Set((selected?.papers ?? []).flatMap((paper) => paper.sources))),
    [selected?.papers],
  );
  const fieldOptions = useMemo(
    () => Array.from(new Set((selected?.papers ?? []).flatMap((paper) => paper.fields))).sort(),
    [selected?.papers],
  );
  const resultLimitOptions = useMemo(
    () =>
      Array.from(
        new Set([
          config.defaults.result_limit,
          10,
          20,
          30,
          40,
          50,
          config.limits.result_max,
        ]),
      )
        .filter((value) => value >= 1 && value <= config.limits.result_max)
        .sort((left, right) => left - right),
    [config.defaults.result_limit, config.limits.result_max],
  );
  const timeOptions = useMemo(() => timeRangeOptions(config), [config]);

  return (
    <main className="research-page">
      <aside className="research-history" aria-label="Research session history">
        <div className="research-history__heading">
          <div>
            <span>Research history</span>
            <strong>Sessions</strong>
          </div>
          <button
            type="button"
            className="research-new-button"
            onClick={startNewSession}
            aria-label="Start a new research session"
            title="New search"
          >
            ＋
          </button>
        </div>
        <div className="research-history__list">
          {loadingHistory && <p className="research-muted">Loading sessions…</p>}
          {!loadingHistory && sessions.length === 0 && (
            <p className="research-muted">Your research sessions will appear here.</p>
          )}
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`research-history-row ${(activeId ? activeId === session.id : selected?.id === session.id) ? "research-history-row--active" : ""}`}
            >
              {editingSessionId === session.id ? (
                <div className="research-history-item research-history-item--editing">
                  <form
                    ref={editingSessionId === session.id ? renameFormRef : undefined}
                    className="research-history-inline-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      void handleRenameSubmit(session);
                    }}
                  >
                    <input
                      type="text"
                      className="research-history-inline-input"
                      value={renameValue}
                      onChange={(event) => setRenameValue(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          event.stopPropagation();
                          cancelRename();
                        }
                      }}
                      autoFocus
                      maxLength={120}
                      disabled={renameSaving}
                      aria-label="Rename session"
                    />
                    <div className="research-history-inline-actions">
                      <button
                        type="submit"
                        className="research-inline-btn research-inline-btn--save"
                        title="Save (Enter)"
                        disabled={renameSaving}
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        className="research-inline-btn research-inline-btn--cancel"
                        title="Cancel (Esc)"
                        onClick={(event) => {
                          event.stopPropagation();
                          cancelRename();
                        }}
                        disabled={renameSaving}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </form>
                  <span className="research-history-item__meta">
                    <span aria-label={session.visibility}>{session.visibility === "public" ? "◉" : "▣"}</span>
                    {session.owner.display_name} · {formatDate(session.created_at)}
                  </span>
                </div>
              ) : (
                <button
                  type="button"
                  className="research-history-item"
                  onClick={() => void selectSession(session.id)}
                >
                  <span className="research-history-item__title">{session.title}</span>
                  <span className="research-history-item__meta">
                    <span aria-label={session.visibility}>{session.visibility === "public" ? "◉" : "▣"}</span>
                    {session.owner.display_name} · {formatDate(session.created_at)}
                  </span>
                  {ACTIVE_RESEARCH_STATUSES.has(session.status) && (
                    <span className={`research-status research-status--${sessionTone(session.status)}`}>
                      {session.status === "queued" && session.queue_position
                        ? `Queued #${session.queue_position}`
                        : session.status.replaceAll("_", " ")}
                    </span>
                  )}
                </button>
              )}
              {session.can_manage && editingSessionId !== session.id && !session.id.startsWith("temp-") && (
                <div className="research-session-menu">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button
                        type="button"
                        className="research-session-menu__trigger"
                        aria-label={`More options for ${session.title}`}
                      >
                        <MoreHorizontal aria-hidden="true" />
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      side="bottom"
                      sideOffset={6}
                      avoidCollisions={true}
                      collisionPadding={{ top: 16, bottom: 32, left: 12, right: 12 }}
                      className="research-session-menu__panel"
                    >
                      <DropdownMenuItem
                        className="research-session-menu__item"
                        disabled={sessionActionId === session.id}
                        onSelect={() => startRename(session)}
                      >
                        <Pencil aria-hidden="true" />
                        Rename
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="research-session-menu__danger"
                        onSelect={() => setSessionToDelete(session)}
                      >
                        <Trash2 aria-hidden="true" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              )}
            </div>
          ))}
          {nextCursor && (
            <button
              type="button"
              className="research-load-more"
              onClick={() => void fetchHistory(nextCursor)}
            >
              Load older sessions
            </button>
          )}
        </div>
      </aside>

      <section className="research-workspace">
        <header className="research-hero">
          <div>
            <p className="research-breadcrumb">⌂ &nbsp;›&nbsp; AI Research Tool</p>
            <h1><span aria-hidden="true">✦</span> AI Research Tool</h1>
            <p>Find, analyze, and compare academic papers with an AI-assisted pipeline.</p>
          </div>
          <blockquote>“Research today, a smarter tomorrow.”<small>— CyVerse</small></blockquote>
        </header>

        <form className="research-search-card" onSubmit={submitSearch}>
          <div className="research-search-card__topline">
            <strong>⌕ &nbsp; Search papers</strong>
            <span>Use a focused research question for better results.</span>
          </div>
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={config.limits.query_max}
            placeholder='e.g. "Recent advances in explainable deepfake detection"'
            aria-label="Research question"
          />
          <div className="research-search-controls">
            <label>
              <span>Time range</span>
              <select
                value={preferences.timeRange}
                onChange={(event) => updatePreference("timeRange", event.target.value as ResearchPreferences["timeRange"])}
              >
                {timeOptions.map((option) => (
                  <option value={option.value} key={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <fieldset className="research-source-picker">
              <legend>Sources</legend>
              <div>
                {config.sources.map((source) => (
                  <label key={source}>
                    <input
                      type="checkbox"
                      checked={preferences.sources.includes(source)}
                      onChange={() => toggleSource(source)}
                    />
                    {SOURCE_LABELS[source]}
                  </label>
                ))}
              </div>
            </fieldset>
            <label>
              <span>Max results</span>
              <select
                value={preferences.resultLimit}
                onChange={(event) => updatePreference("resultLimit", Number(event.target.value))}
              >
                {resultLimitOptions.map((value) => (
                  <option value={value} key={value}>{value} papers</option>
                ))}
              </select>
            </label>
            <label>
              <span>Visibility</span>
              <select
                value={selected ? selected.visibility : visibility}
                onChange={(event) => {
                  const next = event.target.value as ResearchVisibility;
                  setVisibility(next);
                  if (selected && selected.can_manage && !selected.id.startsWith("temp-")) {
                    void changeVisibility(next);
                  }
                }}
              >
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
            </label>
            <button className="primary-button research-submit" type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "➤ Search papers"}
            </button>
          </div>
          {preferences.timeRange === "custom" && (
            <div className="research-custom-years-box">
              <div className="research-custom-years__header">
                <h5>Custom Publication Window</h5>
                <p>Specify the publication range for retrieved papers ({Math.max(config.limits.year_min, 2020)} to {config.limits.year_max}).</p>
              </div>
              <div className="research-custom-years__grid">
                <label>
                  <span>Year from</span>
                  <input
                    type="number"
                    min={Math.max(config.limits.year_min, 2020)}
                    max={config.limits.year_max}
                    value={preferences.yearFrom}
                    placeholder={String(config.defaults.year_from)}
                    onChange={(event) => updatePreference("yearFrom", event.target.value)}
                  />
                  <small>Minimum: {Math.max(config.limits.year_min, 2020)}</small>
                </label>
                <label>
                  <span>Year to</span>
                  <input
                    type="number"
                    min={Math.max(config.limits.year_min, 2020)}
                    max={config.limits.year_max}
                    value={preferences.yearTo}
                    placeholder={String(config.defaults.year_to)}
                    onChange={(event) => updatePreference("yearTo", event.target.value)}
                  />
                  <small>Maximum: {config.limits.year_max}</small>
                </label>
              </div>
            </div>
          )}
          <button
            type="button"
            className="research-advanced-toggle"
            aria-expanded={advancedOpen}
            onClick={() => setAdvancedOpen((current) => !current)}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            <span>{advancedOpen ? "Hide advanced settings" : "Advanced settings"}</span>
            <ChevronDown
              className={`h-3.5 w-3.5 transition-transform duration-200 ${advancedOpen ? "rotate-180" : ""}`}
            />
          </button>
          {advancedOpen && (
            <div className="research-advanced-panel">
              <div className="research-advanced-header">
                <div>
                  <h4 className="research-advanced-title">Candidate Extraction Limits</h4>
                  <p className="research-advanced-desc">
                    Set the maximum raw candidate papers to retrieve from each source before AI ranking.
                  </p>
                </div>
                <button
                  type="button"
                  className="research-reset-button"
                  onClick={resetPreferences}
                  title="Reset retrieval parameters to system defaults"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Reset defaults</span>
                </button>
              </div>

              <div className="research-source-limits-grid">
                {preferences.sources.map((source) => (
                  <div className="research-source-limit-card" key={source}>
                    <div className="research-source-limit-label">
                      <span className="research-source-tag">{SOURCE_LABELS[source]}</span>
                      <span className="research-source-hint">Max {config.limits.raw_per_source_max}</span>
                    </div>
                    <input
                      type="number"
                      min="1"
                      max={config.limits.raw_per_source_max}
                      value={preferences.rawLimits[source] ?? ""}
                      placeholder={String(config.defaults.raw_limits[source] ?? 50)}
                      onChange={(event) =>
                        updatePreference("rawLimits", {
                          ...preferences.rawLimits,
                          [source]: event.target.value,
                        })
                      }
                    />
                    <small>Default: {config.defaults.raw_limits[source] ?? 50} papers</small>
                  </div>
                ))}
              </div>
            </div>
          )}
        </form>

        {error && <div className="research-alert" role="alert">{error}</div>}
        {loadingSession && <div className="research-empty"><div className="research-spinner" />Loading research session…</div>}
        {!loadingSession && !selected && (
          <div className="research-empty">
            <span aria-hidden="true">✦</span>
            <h2>Start a research session</h2>
            <p>Your search will be queued immediately and remain available after you close this page.</p>
          </div>
        )}
        {!loadingSession && selected && (
          <>
            <section className="research-session-header">
              <div className="research-session-header__main">
                <span className={`research-status research-status--${sessionTone(selected.status)}`}>{selected.status.replaceAll("_", " ")}</span>
                {editingSessionId === selected.id ? (
                  <form
                    ref={editingSessionId === selected.id ? renameFormRef : undefined}
                    className="research-header-inline-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void handleRenameSubmit(selected);
                    }}
                  >
                    <input
                      type="text"
                      className="research-header-inline-input"
                      value={renameValue}
                      onChange={(event) => setRenameValue(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") cancelRename();
                      }}
                      autoFocus
                      maxLength={120}
                      disabled={renameSaving}
                      aria-label="Rename session"
                    />
                    <div className="research-header-inline-actions">
                      <button
                        type="submit"
                        className="research-inline-btn research-inline-btn--save"
                        title="Save name (Enter)"
                        disabled={renameSaving}
                      >
                        <Check className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        className="research-inline-btn research-inline-btn--cancel"
                        title="Cancel (Esc)"
                        onClick={cancelRename}
                        disabled={renameSaving}
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="research-header-title-row">
                    <h2>{selected.title}</h2>
                    {selected.can_manage && !selected.id.startsWith("temp-") && (
                      <button
                        type="button"
                        className="research-title-rename-btn"
                        onClick={() => startRename(selected)}
                        title="Rename session"
                        aria-label="Rename session"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                )}
                <p>{selected.owner.display_name} · {formatDate(selected.created_at)}</p>
              </div>
              {selected.can_manage && (
                <div className="research-session-actions">
                  <button
                    type="button"
                    className="secondary-button text-rose-600 hover:text-rose-700 hover:border-rose-300 dark:text-rose-400 dark:hover:border-rose-800"
                    onClick={() => setSessionToDelete(selected)}
                    title="Delete session"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                  {ACTIVE_RESEARCH_STATUSES.has(selected.status) && <button type="button" className="secondary-button" onClick={() => void cancelSelected()}>Cancel</button>}
                </div>
              )}
            </section>

            {ACTIVE_RESEARCH_STATUSES.has(selected.status) && (
              <section className="research-progress-card" aria-live="polite">
                <div className="research-progress-card__heading">
                  <div><strong>{selected.status === "queued" ? `Waiting in queue${selected.queue_position ? ` · position ${selected.queue_position}` : ""}` : "Research in progress"}</strong><span>{selected.events.at(-1)?.message}</span></div>
                  <b>{Math.round(selected.progress * 100)}%</b>
                </div>
                <div className="research-progress-track"><span style={{ width: `${selected.progress * 100}%` }} /></div>
                <ol className="research-progress-events">
                  {selected.events.map((item) => <li key={item.sequence}><span>✓</span><div><strong>{item.stage.replaceAll("_", " ")}</strong><small>{item.message}</small></div></li>)}
                </ol>
              </section>
            )}
            {selected.error && <div className="research-alert" role="alert"><strong>{selected.error.code.replaceAll("_", " ")}</strong><br />{selected.error.message}</div>}
            {selected.warnings.length > 0 && (
              <div className="research-warning" role="status">
                {selected.warnings.map((warning, index) => <p key={index}>{typeof warning.message === "string" ? warning.message : "The search completed with a warning."}</p>)}
              </div>
            )}

            {selected.papers.length > 0 && (
              <section className="research-results">
                <div className="research-results__heading"><div><h2>Search results</h2><span>{papers.length} of {selected.papers.length} papers</span></div><label>Sort by<select value={filters.sort} onChange={(event) => setFilters((current) => ({ ...current, sort: event.target.value as PaperFilters["sort"] }))}><option value="relevance">Relevance</option><option value="newest">Newest</option><option value="citations">Most cited</option><option value="title">Title</option></select></label></div>
                <div className="research-results__layout">
                  <aside className="research-filters" aria-label="Paper filters">
                    <div><strong>Filters</strong><button type="button" onClick={() => setFilters(EMPTY_PAPER_FILTERS)}>Clear</button></div>
                    <label>Publication year<select value={filters.year} onChange={(event) => setFilters((current) => ({ ...current, year: event.target.value }))}><option value="">All years</option>{Array.from(yearCounts).sort((a, b) => b[0].localeCompare(a[0])).map(([value, count]) => <option key={value} value={value}>{value} ({count})</option>)}</select></label>
                    <label>Source<select value={filters.source} onChange={(event) => setFilters((current) => ({ ...current, source: event.target.value }))}><option value="">All sources</option>{sourceOptions.map((value) => <option key={value} value={value}>{SOURCE_LABELS[value]} ({selected.papers.filter((paper) => paper.sources.includes(value)).length})</option>)}</select></label>
                    <label>Paper type<select value={filters.paperType} onChange={(event) => setFilters((current) => ({ ...current, paperType: event.target.value }))}><option value="">All types</option>{Array.from(typeCounts).map(([value, count]) => <option key={value} value={value}>{value} ({count})</option>)}</select></label>
                    <label>Topic<select value={filters.field} onChange={(event) => setFilters((current) => ({ ...current, field: event.target.value }))}><option value="">All topics</option>{fieldOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                    <label>Read priority<select value={filters.priority} onChange={(event) => setFilters((current) => ({ ...current, priority: event.target.value }))}><option value="">All priorities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
                    <label className="research-inline-check">
                      <input
                        type="checkbox"
                        checked={filters.openAccess}
                        onChange={(event) =>
                          setFilters((current) => ({ ...current, openAccess: event.target.checked }))
                        }
                      />
                      <span>Open access only</span>
                    </label>
                  </aside>
                  <div className="research-paper-list">
                    {papers.length === 0 && <div className="research-empty"><h3>No papers match these filters</h3><button type="button" className="secondary-button" onClick={() => setFilters(EMPTY_PAPER_FILTERS)}>Clear filters</button></div>}
                    {papers.map((paper) => {
                      const openUrl = paper.pdf_url ?? paper.landing_url;
                      return <article className="research-paper-card" key={paper.id}>
                        <span className="research-paper-rank">{paper.rank}</span>
                        <div className="research-paper-card__body">
                          <div className="research-paper-card__title"><div><h3>{paper.title}</h3><p>{paper.authors.slice(0, 4).join(", ")}{paper.authors.length > 4 ? ", et al." : ""} · {paper.venue ?? "Unknown venue"} · {formatPaperDate(paper.published_at, paper.year)}</p></div>{openUrl ? <a className="research-open-button" href={openUrl} target="_blank" rel="noopener noreferrer" aria-label={`${paper.pdf_url ? "Open PDF" : "Open source page"} for ${paper.title}`}>Open ↗</a> : <button className="research-open-button" disabled>Unavailable</button>}</div>
                          <div className="research-paper-tags">{paper.sources.map((source) => <span key={source}>{SOURCE_LABELS[source]}</span>)}<span>{paper.paper_type}</span>{paper.is_open_access && <span>Open access</span>}<span>{paper.citation_count ?? 0} citations</span></div>
                          <div className="research-paper-analysis">
                            <section><strong>✦ AI summary</strong><p lang="vi">{paper.summary_vi}</p><small>Analysis based on the abstract.</small></section>
                            <section><strong>Why read this?</strong><ul lang="vi">{paper.why_read_vi.slice(0, 3).map((reason) => <li key={reason}>{reason}</li>)}</ul></section>
                          </div>
                        </div>
                      </article>;
                    })}
                  </div>
                </div>
              </section>
            )}
          </>
        )}
      </section>

      <Dialog
        open={Boolean(sessionToDelete)}
        onOpenChange={(open) => {
          if (!open) setSessionToDelete(null);
        }}
      >
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-1">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400">
                <Trash2 className="h-5 w-5" />
              </div>
              <DialogTitle className="text-base font-semibold text-slate-900 dark:text-slate-100">
                Delete research session
              </DialogTitle>
            </div>
            <DialogDescription className="text-sm text-slate-600 dark:text-slate-300 leading-normal pt-1">
              Are you sure you want to delete <strong className="font-semibold text-slate-900 dark:text-slate-100">“{sessionToDelete?.title}”</strong>? This action cannot be undone and will permanently remove this session and its retrieved papers from your history.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0 mt-2">
            <button
              type="button"
              className="secondary-button"
              onClick={() => setSessionToDelete(null)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white text-sm font-semibold px-4 py-2 transition-colors"
              onClick={() => void confirmDeleteSession()}
            >
              Delete session
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
