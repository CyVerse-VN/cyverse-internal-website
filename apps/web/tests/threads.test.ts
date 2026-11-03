import { describe, expect, it } from "vitest";
import { DEFAULT_THREADS_PARAMETERS, filterThreadsPosts, loadThreadsSettings, parseKeywords, safeThreadsUrl, saveThreadsSettings } from "../src/features/threads/settings";
import { threadsPostSchema, threadsRequestSchema } from "../src/features/threads/types";

describe("Threads parameters", () => {
  it("normalizes keyword input and validates collection limits", () => {
    expect(threadsRequestSchema.parse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel" }).visibility).toBe("public");
    expect(threadsRequestSchema.parse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", visibility: "private" }).visibility).toBe("private");
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", visibility: "unlisted" }).success).toBe(false);
    expect(parseKeywords(" cafes, parks\ncafes, ")).toEqual(["cafes", "parks"]);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", max_posts_per_keyword: 101 }).success).toBe(false);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", max_posts_per_keyword: 75 }).success).toBe(true);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: " " }).success).toBe(false);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "q".repeat(101), expand_query: false }).success).toBe(false);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", max_comments_per_post: -1, max_comment_posts: -1 }).success).toBe(true);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", pre_filter_strictness: "none" }).success).toBe(true);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", pre_filter_strictness: "medium" }).success).toBe(true);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", pre_filter_strictness: "high" }).success).toBe(true);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", max_accounts: 2, use_proxy: false }).success).toBe(true);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", max_accounts: 15 }).success).toBe(false);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", keywords_per_query: 4 }).success).toBe(true);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", keywords_per_query: 10 }).success).toBe(false);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", run_timeout_seconds: -1, search_timeout_seconds: -1 }).success).toBe(true);
    expect(threadsRequestSchema.safeParse({ ...DEFAULT_THREADS_PARAMETERS, query: "travel", search_timeout_seconds: 0 }).success).toBe(false);
  });

  it("restores valid preferences and discards invalid storage", () => {
    let value = "";
    const storage = { getItem: () => value, setItem: (_key: string, next: string) => { value = next; } };
    expect(saveThreadsSettings(storage, { ...DEFAULT_THREADS_PARAMETERS, max_posts_per_keyword: 8 })).toBe(true);
    expect(loadThreadsSettings(storage)?.max_posts_per_keyword).toBe(8);
    expect(saveThreadsSettings(storage, { ...DEFAULT_THREADS_PARAMETERS, max_posts_per_keyword: Number.NaN })).toBe(false);
    expect(loadThreadsSettings(storage)?.max_posts_per_keyword).toBe(8);
    value = '{"max_posts_per_keyword":1000}';
    expect(loadThreadsSettings(storage)).toBeNull();
    value = "invalid JSON";
    expect(loadThreadsSettings(storage)).toBeNull();
  });

  it("filters post text, authors, and AI summaries without losing the source data", () => {
    const base = threadsPostSchema.parse({
      post_id: "one", url: "https://www.threads.com/@sample/post/abcdef", username: "sample",
      text: "A quiet cafe", published_at: null, like_count: 2, reply_count: 0, repost_count: 0,
      images: [], videos: [], search_keywords: ["cafe"], comments: [], ai_analysis: null,
    });
    const relevant = { ...base, post_id: "two", ai_analysis: {
      is_relevant: true, confidence_score: 0.9, topic: "Travel", summary: "Reading spots",
      recommended_places: [], key_entities: [], sentiment: "positive" as const,
    } };
    expect(filterThreadsPosts([base, relevant], "READING", false)).toEqual([relevant]);
    expect(filterThreadsPosts([base, relevant], "", true)).toEqual([relevant]);
    expect(base.ai_analysis).toBeNull();
  });

  it("rejects unsafe source links", () => {
    expect(safeThreadsUrl("https://www.threads.com/@sample/post/abcdef")).toContain("threads.com");
    for (const value of ["javascript:alert(1)", "https://threads.com.evil.example/", "https://user:pass@threads.com/", "http://threads.com/", "https://threads.com:8443/"]) {
      expect(safeThreadsUrl(value)).toBeNull();
    }
  });
});
