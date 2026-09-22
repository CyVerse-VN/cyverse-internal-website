import type { ResearchPaper } from "./types";

export interface PaperFilters {
  year: string;
  source: string;
  paperType: string;
  field: string;
  openAccess: boolean;
  priority: string;
  sort: "relevance" | "newest" | "citations" | "title";
}

export const EMPTY_PAPER_FILTERS: PaperFilters = {
  year: "",
  source: "",
  paperType: "",
  field: "",
  openAccess: false,
  priority: "",
  sort: "relevance",
};

export function filterAndSortPapers(
  papers: ResearchPaper[],
  filters: PaperFilters,
): ResearchPaper[] {
  const filtered = papers.filter(
    (paper) =>
      (!filters.year || String(paper.year) === filters.year) &&
      (!filters.source || paper.sources.includes(filters.source as ResearchPaper["sources"][number])) &&
      (!filters.paperType || paper.paper_type === filters.paperType) &&
      (!filters.field || paper.fields.includes(filters.field)) &&
      (!filters.openAccess || paper.is_open_access === true) &&
      (!filters.priority || paper.read_priority === filters.priority),
  );
  return filtered.sort((left, right) => {
    if (filters.sort === "newest") return (right.year ?? 0) - (left.year ?? 0);
    if (filters.sort === "citations") return (right.citation_count ?? 0) - (left.citation_count ?? 0);
    if (filters.sort === "title") return left.title.localeCompare(right.title);
    return right.relevance_score - left.relevance_score;
  });
}

export function facetCounts(papers: ResearchPaper[], key: "year" | "paper_type"): Map<string, number> {
  const counts = new Map<string, number>();
  for (const paper of papers) {
    const value = key === "year" ? String(paper.year ?? "Unknown") : paper.paper_type;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return counts;
}
