#!/usr/bin/env python3
"""Audit saved pipeline results for relevance, freshness, completeness and API health."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _identity(item: dict[str, Any]) -> str:
    paper = item.get("paper") or {}
    return str(
        item.get("dedup_key") or paper.get("doi") or paper.get("arxiv_id")
        or f"{paper.get('source')}:{paper.get('source_id')}"
    )


def audit(path: Path, minimum_year: int) -> dict[str, Any]:
    result = _load(path)
    papers = result.get("papers") or []
    requested = int((result.get("runtime_config") or {}).get("result_limit") or 0)
    identities = [_identity(item) for item in papers]
    years = [(item.get("paper") or {}).get("year") for item in papers]
    year_violations = [year for year in years if not isinstance(year, int) or year < minimum_year]

    ai_values = [item.get("ai_rerank") for item in papers if item.get("ai_rerank")]
    relevances = [float(item.get("relevance") or 0.0) for item in ai_values]
    high_confidence_irrelevant = [
        item for item in ai_values
        if float(item.get("confidence") or 0.0) >= 0.60
        and float(item.get("relevance") or 0.0) < 0.25
    ]
    summaries = sum(
        bool(((item.get("assessment") or {}).get("paper_analysis") or {}).get("summary"))
        for item in papers
    )
    why_read = sum(
        bool(((item.get("assessment") or {}).get("search_analysis") or {}).get("why_read"))
        for item in papers
    )

    source_health = {}
    rate_limit_errors = []
    for source, value in ((result.get("retrieval") or {}).get("sources") or {}).items():
        errors = value.get("errors") or []
        for error in errors:
            message = str(error.get("error") or "")
            if "429" in message or "rate exceeded" in message.casefold() \
                    or "too many requests" in message.casefold():
                rate_limit_errors.append({"source": source, "error": message})
        source_health[source] = {
            "candidate_count": value.get("candidate_count"),
            "request_count": len(value.get("requests") or []),
            "error_count": len(errors),
        }

    paper_count = len(papers)
    checks = {
        "freshness_pass": not year_violations,
        "duplicate_free_pass": len(identities) == len(set(identities)),
        "summary_coverage_pass": summaries == paper_count,
        "why_read_coverage_pass": why_read == paper_count,
        "relevance_pass": (
            not high_confidence_irrelevant
            and (not relevances or mean(relevances) >= 0.75)
        ),
        "requested_size_met": requested > 0 and paper_count >= requested,
        "rate_limit_clean": not rate_limit_errors,
    }
    quality_checks = [
        "freshness_pass", "duplicate_free_pass", "summary_coverage_pass",
        "why_read_coverage_pass", "relevance_pass",
    ]
    return {
        "file": str(path),
        "pipeline_status": result.get("status"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "minimum_year": minimum_year,
        "requested_result_count": requested,
        "actual_result_count": paper_count,
        "mean_ai_relevance": round(mean(relevances), 6) if relevances else None,
        "ai_reranked_result_count": len(ai_values),
        "summary_count": summaries,
        "why_read_count": why_read,
        "year_violations": year_violations,
        "duplicate_count": len(identities) - len(set(identities)),
        "high_confidence_irrelevant_count": len(high_confidence_irrelevant),
        "rate_limit_errors": rate_limit_errors,
        "source_health": source_health,
        "retrieval": result.get("retrieval"),
        "checks": checks,
        "quality_pass": all(checks[name] for name in quality_checks),
        "overall_pass": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--minimum-year", type=int, default=2025)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = [audit(path, args.minimum_year) for path in args.files]
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "quality_pass_count": sum(bool(case["quality_pass"]) for case in cases),
        "overall_pass_count": sum(bool(case["overall_pass"]) for case in cases),
        "cases": cases,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Saved: {args.output.resolve()}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
