import { z } from "zod";
import { threadsParametersSchema, type ThreadsParameters, type ThreadsPost } from "./types";

const panelPreferencesSchema = z.object({ history_collapsed: z.boolean(), settings_collapsed: z.boolean() });
export type ThreadsPanels = z.infer<typeof panelPreferencesSchema>;
export const DEFAULT_THREADS_PANELS: ThreadsPanels = { history_collapsed: false, settings_collapsed: false };
const PANEL_PREFERENCES_KEY = "cyverse.threads.panels.v1";

export function loadThreadsPanels(storage: Pick<Storage, "getItem">): ThreadsPanels {
  try {
    const raw = storage.getItem(PANEL_PREFERENCES_KEY);
    const parsed = panelPreferencesSchema.safeParse(raw ? JSON.parse(raw) : null);
    return parsed.success ? parsed.data : DEFAULT_THREADS_PANELS;
  } catch {
    return DEFAULT_THREADS_PANELS;
  }
}

export function saveThreadsPanels(storage: Pick<Storage, "setItem">, panels: ThreadsPanels): void {
  try {
    storage.setItem(PANEL_PREFERENCES_KEY, JSON.stringify(panels));
  } catch {
    // Panel preferences are optional when browser storage is unavailable.
  }
}

export const THREADS_SETTINGS_KEY = "cyverse.threads.settings.v2";
const LEGACY_THREADS_SETTINGS_KEY = "cyverse.threads.settings.v1";
export const DEFAULT_THREADS_PARAMETERS: ThreadsParameters = {
  mode: "scraper",
  keywords: [], max_posts_per_keyword: 25, search_type: "recent", check_duplicate: false, include_comments: true,
  max_comment_posts: -1, max_comments_per_post: 25, min_replies: 0,
  expand_query: true, keywords_per_query: 3, pre_filter: false, pre_filter_strictness: "high", curate: false,
  max_accounts: 3, use_proxy: true,
  run_timeout_seconds: 1800, search_timeout_seconds: 120,
  min_delay_seconds: 2, max_delay_seconds: 4,
};

export function parseKeywords(value: string): string[] {
  return [...new Set(value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean))];
}

export function loadThreadsSettings(storage: Pick<Storage, "getItem">): ThreadsParameters | null {
  try {
    const current = storage.getItem(THREADS_SETTINGS_KEY);
    const raw = current ?? storage.getItem(LEGACY_THREADS_SETTINGS_KEY);
    if (!raw) return null;
    const parsed = threadsParametersSchema.safeParse(JSON.parse(raw));
    return parsed.success ? (current === null ? { ...parsed.data, check_duplicate: false } : parsed.data) : null;
  } catch {
    // An unavailable browser store or old preferences must not block a new run.
    return null;
  }
}

export function saveThreadsSettings(storage: Pick<Storage, "setItem">, settings: ThreadsParameters): boolean {
  const parsed = threadsParametersSchema.safeParse(settings);
  if (!parsed.success) return false;
  try {
    storage.setItem(THREADS_SETTINGS_KEY, JSON.stringify(parsed.data));
    return true;
  } catch {
    return false;
  }
}

export function safeThreadsUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password && !url.port &&
      ["threads.com", "www.threads.com", "threads.net", "www.threads.net"].includes(url.hostname)
      ? url.href : null;
  } catch {
    return null;
  }
}

export function filterThreadsPosts(posts: ThreadsPost[], search: string, curatedOnly: boolean): ThreadsPost[] {
  const query = search.trim().toLocaleLowerCase();
  return posts.filter((post) => (!curatedOnly || post.ai_analysis?.is_relevant === true) &&
    (!query || [post.text, post.username, post.ai_analysis?.summary ?? ""]
      .some((value) => value.toLocaleLowerCase().includes(query))));
}

export function isActiveRun(status: string): boolean {
  return status === "queued" || status === "running";
}
