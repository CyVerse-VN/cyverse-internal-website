import { afterEach, describe, expect, it, vi } from "vitest";

import {
  EMPTY_PAPER_FILTERS,
  filterAndSortPapers,
} from "../src/features/research/filters";
import {
  FALLBACK_RESEARCH_CONFIG,
  RESEARCH_STORAGE_KEY,
  defaultPreferences,
  loadPreferences,
  savePreferences,
  timeRangeOptions,
  toResearchSettings,
} from "../src/features/research/settings";
import type { ResearchPaper } from "../src/features/research/types";

const papers: ResearchPaper[] = [
  {
    id: "one",
    rank: 1,
    relevance_score: 0.9,
    read_priority: "high",
    title: "Clinical RAG",
    authors: ["A. Researcher"],
    year: 2026,
    published_at: "2026-01-01",
    venue: "Journal",
    doi: "10.1000/one",
    arxiv_id: null,
    sources: ["openalex"],
    paper_type: "article",
    fields: ["Medicine"],
    citation_count: 10,
    is_open_access: true,
    pdf_url: "https://example.com/one.pdf",
    landing_url: "https://example.com/one",
    summary_vi: "Nghiên cứu phân tích hệ thống RAG trong y khoa.",
    why_read_vi: ["Cung cấp đánh giá thực nghiệm rõ ràng."],
    analysis_basis: "abstract",
  },
  {
    id: "two",
    rank: 2,
    relevance_score: 0.7,
    read_priority: "medium",
    title: "Older Survey",
    authors: ["B. Researcher"],
    year: 2024,
    published_at: null,
    venue: null,
    doi: null,
    arxiv_id: "2401.00001",
    sources: ["arxiv"],
    paper_type: "review",
    fields: ["Computer Science"],
    citation_count: 40,
    is_open_access: true,
    pdf_url: null,
    landing_url: "https://arxiv.org/abs/2401.00001",
    summary_vi: "Bài tổng quan hệ thống hóa các hướng nghiên cứu liên quan.",
    why_read_vi: ["Giúp nắm nhanh bối cảnh và khoảng trống nghiên cứu."],
    analysis_basis: "abstract",
  },
];

describe("research settings", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses the balanced defaults and derives the three-year window", () => {
    const preferences = defaultPreferences(FALLBACK_RESEARCH_CONFIG);
    const settings = toResearchSettings(FALLBACK_RESEARCH_CONFIG, preferences);

    expect(settings.result_limit).toBe(20);
    expect(settings.sources).toEqual(["semantic_scholar", "arxiv", "openalex"]);
    expect(settings.year_to! - settings.year_from!).toBe(2);
  });

  it("offers start-year presets through the present year", () => {
    const options = timeRangeOptions(FALLBACK_RESEARCH_CONFIG);
    const presentYear = FALLBACK_RESEARCH_CONFIG.defaults.year_to!;

    expect(options[0]).toEqual({
      value: `from-${presentYear - 1}`,
      label: `From ${presentYear - 1} to present`,
    });
    expect(options).toContainEqual({
      value: `from-${presentYear - 2}`,
      label: `From ${presentYear - 2} to present`,
    });
  });

  it("limits time range options to 2020 onwards", () => {
    const options = timeRangeOptions(FALLBACK_RESEARCH_CONFIG);

    expect(options).toContainEqual({
      value: "from-2020",
      label: "From 2020 to present",
    });
    expect(options.some((opt) => opt.value === "from-2019")).toBe(false);
    expect(options.some((opt) => opt.value === "all")).toBe(false);
    expect(options.at(-1)).toEqual({
      value: "custom",
      label: "Custom range",
    });
  });

  it("enforces 2020 minimum year limit for custom range and start presets", () => {
    const preferences = {
      ...defaultPreferences(FALLBACK_RESEARCH_CONFIG),
      timeRange: "custom" as const,
      yearFrom: "2018",
      yearTo: "2025",
    };

    const settings = toResearchSettings(FALLBACK_RESEARCH_CONFIG, preferences);

    expect(settings.year_from).toBe(2020);
    expect(settings.year_to).toBe(2025);
  });

  it("converts a start-year preset to an inclusive backend range", () => {
    const presentYear = FALLBACK_RESEARCH_CONFIG.defaults.year_to!;
    const preferences = {
      ...defaultPreferences(FALLBACK_RESEARCH_CONFIG),
      timeRange: `from-${presentYear - 1}` as const,
    };

    const settings = toResearchSettings(FALLBACK_RESEARCH_CONFIG, preferences);

    expect(settings.year_from).toBe(presentYear - 1);
    expect(settings.year_to).toBe(presentYear);
  });

  it("keeps blank raw-limit fields as backend defaults", () => {
    const settings = toResearchSettings(
      FALLBACK_RESEARCH_CONFIG,
      defaultPreferences(FALLBACK_RESEARCH_CONFIG),
    );

    expect(settings.raw_limits).toEqual({});
  });

  it("discards invalid persisted overrides", () => {
    const stored = JSON.stringify({
      schemaVersion: FALLBACK_RESEARCH_CONFIG.schema_version,
      values: {
        sources: ["arxiv", "unknown"],
        resultLimit: 500,
        timeRange: "custom",
        yearFrom: "1800",
        yearTo: "2025",
        rawLimits: { arxiv: "101", openalex: "25" },
        languages: 42,
        openAccessOnly: "yes",
        requireAbstract: false,
      },
    });
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (key: string) => (key === RESEARCH_STORAGE_KEY ? stored : null),
      },
    });

    const preferences = loadPreferences(FALLBACK_RESEARCH_CONFIG);

    expect(preferences.sources).toEqual(["arxiv"]);
    expect(preferences.resultLimit).toBe(20);
    expect(preferences.yearFrom).toBe("");
    expect(preferences.yearTo).toBe("2025");
    expect(preferences.rawLimits).toEqual({ openalex: "25" });
    expect(preferences.languages).toBe("");
    expect(preferences.openAccessOnly).toBe(false);
    expect(preferences.requireAbstract).toBe(false);
  });

  it("resets persisted values when the config schema changes", () => {
    vi.stubGlobal("window", {
      localStorage: {
        getItem: () => JSON.stringify({ schemaVersion: "outdated", values: { resultLimit: 50 } }),
      },
    });

    expect(loadPreferences(FALLBACK_RESEARCH_CONFIG)).toEqual(
      defaultPreferences(FALLBACK_RESEARCH_CONFIG),
    );
  });

  it("persists only overrides so reset remains tied to backend defaults", () => {
    let stored = "";
    vi.stubGlobal("window", {
      localStorage: {
        setItem: (_key: string, value: string) => {
          stored = value;
        },
      },
    });

    savePreferences(
      FALLBACK_RESEARCH_CONFIG,
      defaultPreferences(FALLBACK_RESEARCH_CONFIG),
    );

    expect(JSON.parse(stored)).toEqual({
      schemaVersion: FALLBACK_RESEARCH_CONFIG.schema_version,
      values: {},
    });
  });
});

describe("client paper filtering", () => {
  it("filters without changing the input list", () => {
    const result = filterAndSortPapers(papers, {
      ...EMPTY_PAPER_FILTERS,
      source: "openalex",
      paperType: "article",
    });

    expect(result.map((paper) => paper.id)).toEqual(["one"]);
    expect(papers).toHaveLength(2);
  });

  it("sorts by citations entirely in memory", () => {
    const result = filterAndSortPapers(papers, {
      ...EMPTY_PAPER_FILTERS,
      sort: "citations",
    });

    expect(result.map((paper) => paper.id)).toEqual(["two", "one"]);
  });
});
