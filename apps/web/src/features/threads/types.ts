import { z } from "zod";

export const threadsParametersSchema = z.object({
  mode: z.enum(["scraper", "travel"]).default("scraper"),
  discovery_query_planning: z.boolean().default(true),
  discovery_max_queries: z.number().int().min(1).max(20).default(10),
  discovery_comment_budget: z.number().int().min(1).max(100).default(20),
  keywords: z.array(z.string().trim().min(1).max(100)).max(20),
  max_posts_per_keyword: z.number().int().min(1).max(100).default(25),
  search_type: z.enum(["top", "recent", "both"]),
  check_duplicate: z.boolean().default(false),
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
  discovery_mode: z.enum(["legacy", "evidence_poi"]).default("legacy"),
  query_planning: z.boolean().default(true),
  triage_provider: z.enum(["groq", "jev"]).default("groq"),
  discovery_comment_posts: z.number().int().min(1).max(50).default(20),
  use_manual_keywords: z.boolean().default(true),
});

export const threadsRequestSchema = threadsParametersSchema.extend({
  query: z.string().trim().min(1, "Enter a search question.").max(1000),
  visibility: z.enum(["public", "private"]).default("public"),
}).refine((value) => value.keywords.length > 0 || value.expand_query || value.query.length <= 100 ||
  (value.discovery_mode === "evidence_poi" && (value.discovery_query_planning || value.query_planning)), {
  message: "Supply short keywords or enable query expansion for a longer question.",
  path: ["query"],
}).refine((value) => value.discovery_mode === "legacy" || value.mode === "travel", {
  message: "Discovery mode is only available in travel mode.",
  path: ["discovery_mode"],
});

const postTriageSchema = z.object({
  geo_match: z.enum(["yes", "no", "uncertain"]),
  topic_relevance: z.number(),
  direct_poi_score: z.number(),
  discussion_poi_score: z.number(),
  promotion_risk: z.number(),
  reasons: z.array(z.string()).default([]),
  provider: z.string().default("unknown"),
});

export const postDiscoverySchema = z.object({
  triage: postTriageSchema.nullable().optional(),
  route: z.enum(["direct", "discussion", "both", "excluded", "unclassified"]).default("unclassified"),
  rank_score: z.number().nullable().optional(),
  comment_status: z.enum(["not_attempted", "completed", "partial", "failed"]).default("not_attempted"),
  comment_error: z.string().nullable().optional(),
});

export const poiClaimSchema = z.object({
  claim_type: z.string(),
  value: z.string(),
  evidence_text: z.string(),
  source_post_id: z.string().nullable().optional(),
  source_comment_id: z.string().nullable().optional(),
  confidence: z.number().default(1.0),
});

export const poiMentionSchema = z.object({
  source_post_id: z.string(),
  source_comment_id: z.string().nullable().optional(),
  evidence_text: z.string(),
  confidence: z.number().default(1.0),
});

export const poiCandidateSchema = z.object({
  id: z.string(),
  canonical_name: z.string(),
  category: z.string().nullable().optional(),
  area: z.string().nullable().optional(),
  address: z.string().nullable().optional(),
  verification_status: z.enum(["candidate", "verified", "rejected"]).default("candidate"),
  mentions: z.array(poiMentionSchema).default([]),
  claims: z.array(poiClaimSchema).default([]),
  distinct_sources_count: z.number().default(1),
});

export type POICandidate = z.infer<typeof poiCandidateSchema>;
export type POIClaim = z.infer<typeof poiClaimSchema>;
export type POIMention = z.infer<typeof poiMentionSchema>;

export const discoverySummarySchema = z.object({
  plan: z.object({
    topic: z.string().default(""),
    geographic_scope: z.string().nullable().optional(),
    desired_attributes: z.array(z.string()).default([]),
    exclusions: z.array(z.string()).default([]),
    queries: z.array(z.object({
      text: z.string(),
      angle: z.string(),
      target_content: z.string(),
      origin: z.string(),
      rationale: z.string().default(""),
    })).default([]),
  }).nullable().optional(),
  triage_provider: z.string().nullable().optional(),
  direct_posts: z.number().default(0),
  discussion_posts: z.number().default(0),
  excluded_posts: z.number().default(0),
  unclassified_posts: z.number().default(0),
  comment_posts_selected: z.number().default(0),
  comment_posts_completed: z.number().default(0),
  comment_posts_failed: z.number().default(0),
  warnings: z.array(z.string()).default([]),
  poi_candidates: z.array(poiCandidateSchema).default([]),
}).passthrough();

const commentSchema = z.object({
  id: z.string(), username: z.string(), text: z.string(), like_count: z.number(),
  depth: z.number(), reply_to_username: z.string().nullable(), parent_id: z.string().nullable(),
});

export const threadsPostSchema = z.object({
  post_id: z.string(), url: z.string(), username: z.string(), text: z.string(),
  published_at: z.string().nullable(), like_count: z.number(), reply_count: z.number(),
  repost_count: z.number(), images: z.array(z.string()), videos: z.array(z.string()),
  search_keywords: z.array(z.string()), comments: z.array(commentSchema),
  triage: z.object({
    geo_match: z.enum(["yes", "no", "uncertain"]), topic_relevance: z.number(),
    direct_poi_score: z.number(), discussion_poi_score: z.number(), promotion_risk: z.number(),
    reasons: z.array(z.string()), provider: z.string(), model: z.string().default(""),
  }).nullable().default(null),
  comment_collection_status: z.enum(["not_attempted", "completed", "partial", "failed"]).default("not_attempted"),
  ai_analysis: z.object({
    is_relevant: z.boolean(), confidence_score: z.number(), topic: z.string(), summary: z.string(),
    recommended_places: z.array(z.object({
      name: z.string(), category: z.string(), address_or_area: z.string(), note: z.string(),
    })),
    key_entities: z.array(z.string()), sentiment: z.enum(["positive", "neutral", "negative"]),
  }).nullable(),
  discovery: postDiscoverySchema.nullable().optional(),
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
    discovery: discoverySummarySchema.nullable().optional(),
  }).nullable(),
  error_code: z.string().nullable(), error_message: z.string().nullable(),
  created_at: z.string(), completed_at: z.string().nullable(),
});

export const threadsConfigSchema = z.object({
  enabled: z.boolean(), accounts_ready: z.boolean(), ai_available: z.boolean(),
  cloudinary_ready: z.boolean(),
  defaults: threadsParametersSchema, limits: z.record(z.string(), z.number()),
  triage_providers: z.array(z.string()).default(["groq"]),
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
export type DiscoverySummary = z.infer<typeof discoverySummarySchema>;
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
