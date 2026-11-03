import { z } from "zod";

export const threadsParametersSchema = z.object({
  mode: z.enum(["scraper", "travel"]).default("scraper"),
  keywords: z.array(z.string().trim().min(1).max(100)).max(20),
  max_posts_per_keyword: z.number().int().min(1).max(100).default(25),
  search_type: z.enum(["top", "recent", "both"]),
  check_duplicate: z.boolean().default(true),
  include_comments: z.boolean(),
  max_comment_posts: z.number().int().min(-1).max(500).default(-1),
  max_comments_per_post: z.number().int().min(-1).max(500),
  min_replies: z.number().int().min(0).max(10000).default(0),
  expand_query: z.boolean(),
  keywords_per_query: z.number().int().min(1).max(5).default(3),
  pre_filter: z.boolean(),
  pre_filter_strictness: z.enum(["high", "medium", "none"]).default("high"),
  curate: z.boolean().default(false),
  max_accounts: z.number().int().min(-1).max(10).default(3),
  use_proxy: z.boolean().default(true),
  run_timeout_seconds: z.number().int().min(-1).max(86400).default(1800),
  search_timeout_seconds: z.number().int().min(-1).max(600)
    .refine((value) => value === -1 || value >= 15).default(120),
  min_delay_seconds: z.number().min(0).max(60).default(2),
  max_delay_seconds: z.number().min(0).max(60).default(4),
});

export const threadsRequestSchema = threadsParametersSchema.extend({
  query: z.string().trim().min(1, "Enter a search question.").max(1000),
  visibility: z.enum(["public", "private"]).default("public"),
}).refine((value) => value.keywords.length > 0 || value.expand_query || value.query.length <= 100, {
  message: "Supply short keywords or enable query expansion for a longer question.",
  path: ["query"],
});

const commentSchema = z.object({
  id: z.string(), username: z.string(), text: z.string(), like_count: z.number(),
  depth: z.number(), reply_to_username: z.string().nullable(), parent_id: z.string().nullable(),
});

export const threadsPostSchema = z.object({
  post_id: z.string(), url: z.string(), username: z.string(), text: z.string(),
  published_at: z.string().nullable(), like_count: z.number(), reply_count: z.number(),
  repost_count: z.number(), images: z.array(z.string()), videos: z.array(z.string()),
  search_keywords: z.array(z.string()), comments: z.array(commentSchema),
  ai_analysis: z.object({
    is_relevant: z.boolean(), confidence_score: z.number(), topic: z.string(), summary: z.string(),
    recommended_places: z.array(z.object({
      name: z.string(), category: z.string(), address_or_area: z.string(), note: z.string(),
    })),
    key_entities: z.array(z.string()), sentiment: z.enum(["positive", "neutral", "negative"]),
  }).nullable(),
});

export const threadsRunSchema = z.object({
  id: z.uuid(), status: z.enum(["queued", "running", "completed", "failed", "cancelled"]),
  stage: z.string(), progress: z.number(), request: threadsRequestSchema,
  visibility: z.enum(["public", "private"]),
  owner: z.object({ id: z.uuid(), display_name: z.string().nullable() }).nullable(),
  can_manage: z.boolean(), post_count: z.number(), comment_count: z.number(),
  archive_status: z.enum(["pending", "uploading", "ready", "failed"]),
  archive_uploaded_at: z.string().nullable(), storage_error: z.string().nullable(),
  deletion_requested: z.boolean(), started_at: z.string().nullable(),
  result: z.object({
    query: z.string(), keywords: z.array(z.string()), posts: z.array(threadsPostSchema),
    curated_post_ids: z.array(z.string()), total_comments: z.number(), duplicate_count: z.number().default(0),
    duration_seconds: z.number(), warnings: z.array(z.string()),
  }).nullable(),
  error_code: z.string().nullable(), error_message: z.string().nullable(),
  created_at: z.string(), completed_at: z.string().nullable(),
});

export const threadsConfigSchema = z.object({
  enabled: z.boolean(), accounts_ready: z.boolean(), ai_available: z.boolean(),
  cloudinary_ready: z.boolean(),
  txt_archive_enabled: z.boolean().default(false),
  defaults: threadsParametersSchema, limits: z.record(z.string(), z.number()),
});

export const keywordGroupItemSchema = z.object({
  category: z.string(),
  keywords: z.array(z.string()),
});

export const keywordAnalysisResponseSchema = z.object({
  keywords: z.array(z.string()),
  groups: z.array(keywordGroupItemSchema).default([]),
});

export type ThreadsParameters = z.infer<typeof threadsParametersSchema>;
export type ThreadsRequest = z.infer<typeof threadsRequestSchema>;
export type ThreadsRun = z.infer<typeof threadsRunSchema>;
export type ThreadsPost = z.infer<typeof threadsPostSchema>;
export type ThreadsConfig = z.infer<typeof threadsConfigSchema>;
export type KeywordGroupItem = z.infer<typeof keywordGroupItemSchema>;
export type KeywordAnalysisResponse = z.infer<typeof keywordAnalysisResponseSchema>;

export interface ThreadsAccountItem {
  id: string;
  username: string | null;
  enabled: boolean;
  has_session: boolean;
  is_expired?: boolean;
  expires_at?: string | null;
}
