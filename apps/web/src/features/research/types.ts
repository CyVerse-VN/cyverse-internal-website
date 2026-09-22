export type ResearchSource = "semantic_scholar" | "arxiv" | "openalex";
export type ResearchVisibility = "public" | "private";
export type ResearchStatus =
  | "queued"
  | "running"
  | "completed"
  | "completed_with_warnings"
  | "failed"
  | "cancelled";

export interface ResearchSettings {
  sources: ResearchSource[];
  raw_limits: Partial<Record<ResearchSource, number>>;
  result_limit: number;
  all_years: boolean;
  year_from: number | null;
  year_to: number | null;
  publication_types: string[];
  languages: string[];
  open_access_only: boolean;
  require_abstract: boolean;
}

export interface ResearchConfig {
  schema_version: string;
  default_visibility: ResearchVisibility;
  sources: ResearchSource[];
  publication_types: string[];
  defaults: ResearchSettings;
  limits: Record<string, number>;
}

export interface ResearchOwner {
  id: string;
  display_name: string;
}

export interface ResearchSessionSummary {
  id: string;
  query: string;
  title: string;
  visibility: ResearchVisibility;
  owner: ResearchOwner;
  is_owner: boolean;
  can_manage: boolean;
  status: ResearchStatus;
  current_stage: string;
  progress: number;
  queue_position: number | null;
  result_count: number;
  created_at: string;
  updated_at: string;
}

export interface ResearchProgressEvent {
  sequence: number;
  stage: string;
  status: string;
  message: string;
  progress: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ResearchPaper {
  id: string;
  rank: number;
  relevance_score: number;
  read_priority: "high" | "medium" | "low";
  title: string;
  authors: string[];
  year: number | null;
  published_at: string | null;
  venue: string | null;
  doi: string | null;
  arxiv_id: string | null;
  sources: ResearchSource[];
  paper_type: string;
  fields: string[];
  citation_count: number | null;
  is_open_access: boolean | null;
  pdf_url: string | null;
  landing_url: string | null;
  summary_vi: string;
  why_read_vi: string[];
  analysis_basis: "abstract";
}

export interface ResearchSessionDetail extends ResearchSessionSummary {
  effective_settings: ResearchSettings;
  pipeline_version: string;
  warnings: Array<Record<string, unknown>>;
  result_stats: Record<string, unknown>;
  error: { code: string; message: string } | null;
  events: ResearchProgressEvent[];
  papers: ResearchPaper[];
}

export interface ResearchSessionList {
  items: ResearchSessionSummary[];
  next_cursor: string | null;
}

export const ACTIVE_RESEARCH_STATUSES = new Set<ResearchStatus>(["queued", "running"]);
