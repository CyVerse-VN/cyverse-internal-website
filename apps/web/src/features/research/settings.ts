import type { ResearchConfig, ResearchSettings, ResearchSource } from "./types";

export const RESEARCH_STORAGE_KEY = "cyverse.research.settings.v1";

const currentYear = new Date().getUTCFullYear();

export const FALLBACK_RESEARCH_CONFIG: ResearchConfig = {
  schema_version: "1",
  default_visibility: "public",
  sources: ["semantic_scholar", "arxiv", "openalex"],
  publication_types: ["article", "conference", "preprint", "review", "book", "dataset"],
  defaults: {
    sources: ["semantic_scholar", "arxiv", "openalex"],
    raw_limits: { semantic_scholar: 50, arxiv: 50, openalex: 50 },
    result_limit: 20,
    all_years: false,
    year_from: currentYear - 2,
    year_to: currentYear,
    publication_types: [],
    languages: [],
    open_access_only: false,
    require_abstract: true,
  },
  limits: {
    query_min: 3,
    query_max: 1000,
    year_min: 2020,
    year_max: currentYear + 1,
    raw_per_source_max: 100,
    total_raw_max: 300,
    result_max: 50,
  },
};

export type TimeRange = "all" | "custom" | `from-${number}`;

export interface TimeRangeOption {
  value: TimeRange;
  label: string;
}

export interface ResearchPreferences {
  sources: ResearchSource[];
  resultLimit: number;
  timeRange: TimeRange;
  yearFrom: string;
  yearTo: string;
  rawLimits: Partial<Record<ResearchSource, string>>;
  publicationTypes: string[];
  languages: string;
  openAccessOnly: boolean;
  requireAbstract: boolean;
}

export function defaultPreferences(config: ResearchConfig): ResearchPreferences {
  const minYear = Math.max(config.limits.year_min, 2020);
  const defaultStart = Math.max(
    config.defaults.year_from ?? new Date().getUTCFullYear() - 2,
    minYear,
  );
  return {
    sources: [...config.defaults.sources],
    resultLimit: config.defaults.result_limit,
    timeRange: `from-${defaultStart}`,
    yearFrom: "",
    yearTo: "",
    rawLimits: {},
    publicationTypes: [],
    languages: "",
    openAccessOnly: false,
    requireAbstract: true,
  };
}

export function loadPreferences(config: ResearchConfig): ResearchPreferences {
  const fallback = defaultPreferences(config);
  if (typeof window === "undefined") return fallback;
  try {
    const stored = JSON.parse(window.localStorage.getItem(RESEARCH_STORAGE_KEY) ?? "null") as {
      schemaVersion?: unknown;
      values?: Partial<ResearchPreferences>;
    } | null;
    if (!stored || stored.schemaVersion !== config.schema_version || !stored.values) return fallback;
    const values = stored.values;
    const sources = Array.isArray(values.sources)
      ? values.sources.filter((source): source is ResearchSource => config.sources.includes(source))
      : fallback.sources;
    const resultLimit = Number(values.resultLimit);
    const timeRange = validTimeRange(values.timeRange, config)
      ? values.timeRange
      : fallback.timeRange;
    const yearFrom = validStoredYear(values.yearFrom, config) ? values.yearFrom : "";
    const yearTo = validStoredYear(values.yearTo, config) ? values.yearTo : "";
    const rawLimits: Partial<Record<ResearchSource, string>> = {};
    if (values.rawLimits && typeof values.rawLimits === "object") {
      for (const source of config.sources) {
        const value = values.rawLimits[source];
        const parsed = Number(value);
        if (
          typeof value === "string" &&
          Number.isInteger(parsed) &&
          parsed >= 1 &&
          parsed <= config.limits.raw_per_source_max
        ) {
          rawLimits[source] = value;
        }
      }
    }
    return {
      sources: sources.length ? Array.from(new Set(sources)) : fallback.sources,
      resultLimit:
        Number.isInteger(resultLimit) && resultLimit >= 1 && resultLimit <= config.limits.result_max
          ? resultLimit
          : fallback.resultLimit,
      timeRange,
      yearFrom,
      yearTo,
      publicationTypes: Array.isArray(values.publicationTypes)
        ? values.publicationTypes.filter((value) => config.publication_types.includes(value))
        : [],
      rawLimits,
      languages: typeof values.languages === "string" ? values.languages : "",
      openAccessOnly:
        typeof values.openAccessOnly === "boolean"
          ? values.openAccessOnly
          : fallback.openAccessOnly,
      requireAbstract:
        typeof values.requireAbstract === "boolean"
          ? values.requireAbstract
          : fallback.requireAbstract,
    };
  } catch {
    return fallback;
  }
}

function validStoredYear(value: unknown, config: ResearchConfig): value is string {
  if (value === "") return true;
  if (typeof value !== "string") return false;
  const parsed = Number(value);
  const minYear = Math.max(config.limits.year_min, 2020);
  return (
    Number.isInteger(parsed) &&
    parsed >= minYear &&
    parsed <= config.limits.year_max
  );
}

function validTimeRange(value: unknown, config: ResearchConfig): value is TimeRange {
  if (value === "custom") return true;
  if (typeof value !== "string") return false;
  const match = /^from-(\d{4})$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const minYear = Math.max(config.limits.year_min, 2020);
  const currentYear = config.defaults.year_to ?? new Date().getUTCFullYear();
  return year >= minYear && year <= currentYear;
}

export function timeRangeOptions(config: ResearchConfig): TimeRangeOption[] {
  const currentYear = config.defaults.year_to ?? new Date().getUTCFullYear();
  const minYear = Math.max(config.limits.year_min, 2020);
  const options: TimeRangeOption[] = [];
  for (let year = currentYear - 1; year >= minYear; year -= 1) {
    options.push({ value: `from-${year}`, label: `From ${year} to present` });
  }
  options.push(
    { value: "custom", label: "Custom range" },
  );
  return options;
}

export function savePreferences(config: ResearchConfig, values: ResearchPreferences): void {
  const defaults = defaultPreferences(config);
  const overrides: Partial<ResearchPreferences> = {};
  if (!sameArray(values.sources, defaults.sources)) overrides.sources = values.sources;
  if (values.resultLimit !== defaults.resultLimit) overrides.resultLimit = values.resultLimit;
  if (values.timeRange !== defaults.timeRange) overrides.timeRange = values.timeRange;
  if (values.yearFrom) overrides.yearFrom = values.yearFrom;
  if (values.yearTo) overrides.yearTo = values.yearTo;
  const rawLimits = Object.fromEntries(
    Object.entries(values.rawLimits).filter(([, value]) => Boolean(value)),
  );
  if (Object.keys(rawLimits).length) overrides.rawLimits = rawLimits;
  if (!sameArray(values.publicationTypes, defaults.publicationTypes)) {
    overrides.publicationTypes = values.publicationTypes;
  }
  if (values.languages.trim()) overrides.languages = values.languages;
  if (values.openAccessOnly !== defaults.openAccessOnly) {
    overrides.openAccessOnly = values.openAccessOnly;
  }
  if (values.requireAbstract !== defaults.requireAbstract) {
    overrides.requireAbstract = values.requireAbstract;
  }
  window.localStorage.setItem(
    RESEARCH_STORAGE_KEY,
    JSON.stringify({ schemaVersion: config.schema_version, values: overrides }),
  );
}

function sameArray(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

export function toResearchSettings(
  config: ResearchConfig,
  preferences: ResearchPreferences,
): ResearchSettings {
  const currentYear = config.defaults.year_to ?? new Date().getUTCFullYear();
  const minYear = Math.max(config.limits.year_min, 2020);
  const rawLimits: Partial<Record<ResearchSource, number>> = {};
  for (const source of preferences.sources) {
    const parsed = Number(preferences.rawLimits[source]);
    if (Number.isInteger(parsed) && parsed >= 1) {
      rawLimits[source] = Math.min(parsed, config.limits.raw_per_source_max);
    } else if (preferences.resultLimit > config.defaults.result_limit) {
      const scaled = Math.min(
        Math.max(config.defaults.raw_limits[source] ?? 50, Math.ceil(preferences.resultLimit * 1.6)),
        config.limits.raw_per_source_max,
      );
      rawLimits[source] = scaled;
    }
  }
  const languages = preferences.languages
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter((value) => /^[a-z]{2,3}$/.test(value))
    .slice(0, 5);
  const customFrom = Number(preferences.yearFrom);
  const customTo = Number(preferences.yearTo);
  const selectedStart = preferences.timeRange.startsWith("from-")
    ? Number(preferences.timeRange.slice("from-".length))
    : null;
  return {
    sources: preferences.sources,
    raw_limits: rawLimits,
    result_limit: preferences.resultLimit,
    all_years: false,
    year_from:
      selectedStart !== null && Number.isInteger(selectedStart)
        ? Math.max(selectedStart, minYear)
        : preferences.timeRange === "custom" && Number.isInteger(customFrom)
          ? Math.max(customFrom, minYear)
          : preferences.timeRange === "all"
            ? minYear
            : null,
    year_to:
      selectedStart !== null && Number.isInteger(selectedStart)
        ? currentYear
        : preferences.timeRange === "custom" && Number.isInteger(customTo)
          ? customTo
          : preferences.timeRange === "all"
            ? currentYear
            : null,
    publication_types: preferences.publicationTypes,
    languages: Array.from(new Set(languages)),
    open_access_only: preferences.openAccessOnly,
    require_abstract: preferences.requireAbstract,
  };
}
