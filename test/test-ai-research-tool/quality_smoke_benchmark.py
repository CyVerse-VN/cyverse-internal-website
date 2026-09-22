#!/usr/bin/env python3
"""Run several end-to-end searches and audit recency, relevance and rate limits."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import config
from common import configure_utf8_console, save_json
from research_pipeline import run_pipeline


CASES = [
    {
        "name": "deepfake_detection_since_2025",
        "prompt": "Find recent papers on deepfake detection and media forensics published from 2025 onward",
        "groups": [
            ["deepfake", "face forgery", "synthetic media", "manipulated media"],
            ["detect", "detection", "detector", "forensic", "classification"],
        ],
    },
    {
        "name": "medical_rag_hallucination_since_2025",
        "prompt": "Find papers from 2025 onward about retrieval augmented generation for reducing hallucinations in medical or clinical LLMs",
        "groups": [
            ["retrieval augmented", "retrieval-augmented", " rag "],
            ["medical", "clinical", "healthcare", "biomedical", "health care"],
            ["hallucination", "factuality", "faithfulness", "grounded", "accuracy"],
        ],
    },
    {
        "name": "gnn_traffic_forecasting_since_2025",
        "prompt": "Find papers from 2025 onward about graph neural networks for traffic forecasting",
        "groups": [
            ["graph neural", "graph convolution", "gnn", "spatiotemporal graph", "spatio-temporal graph"],
            ["traffic forecast", "traffic prediction", "traffic flow", "transportation forecast"],
        ],
    },
]


def _searchable_text(item: dict[str, Any]) -> str:
    paper = item.get("paper") or {}
    return " " + re.sub(
        r"\s+", " ", f"{paper.get('title') or ''} {paper.get('abstract') or ''}"
    ).casefold() + " "


def _audit_paper(item: dict[str, Any], groups: list[list[str]], year_from: int) -> dict[str, Any]:
    paper = item.get("paper") or {}
    text = _searchable_text(item)
    group_hits = [any(term.casefold() in text for term in group) for group in groups]
    ai = item.get("ai_rerank") or {}
    ai_relevance = ai.get("relevance") if isinstance(ai.get("relevance"), (int, float)) else None
    ai_confidence = ai.get("confidence") if isinstance(ai.get("confidence"), (int, float)) else None
    lexical_groups = sum(group_hits)
    # AI may bridge vocabulary, but it cannot replace almost all required lexical evidence.
    relevant = all(group_hits) or bool(
        ai_relevance is not None
        and ai_confidence is not None
        and ai_relevance >= 0.75
        and ai_confidence >= 0.50
        and lexical_groups >= max(len(groups) - 1, 1)
    )
    analysis = (item.get("assessment") or {}).get("paper_analysis") or {}
    return {
        "rank": item.get("rank"),
        "title": paper.get("title"),
        "year": paper.get("year"),
        "source": paper.get("source"),
        "group_hits": group_hits,
        "ai_relevance": ai_relevance,
        "ai_confidence": ai_confidence,
        "relevant": relevant,
        "year_ok": isinstance(paper.get("year"), int) and paper["year"] >= year_from,
        "has_abstract": bool(paper.get("abstract")),
        "has_url": bool(paper.get("url")),
        "has_summary": bool(analysis.get("summary")),
    }


def audit_result(result: dict[str, Any], case: dict[str, Any], year_from: int) -> dict[str, Any]:
    papers = [
        _audit_paper(item, case["groups"], year_from)
        for item in result.get("papers") or []
    ]
    count = len(papers)
    sources = (result.get("retrieval") or {}).get("sources") or {}
    rate_limit_errors = [
        {"source": source, "query": error.get("query"), "error": error.get("error")}
        for source, source_data in sources.items()
        for error in source_data.get("errors") or []
        if "429" in str(error.get("error"))
    ]
    contributing_sources = sorted({
        source
        for item in result.get("papers") or []
        for source in (item.get("retrieval_by_source") or {})
    })
    relevant_count = sum(bool(item["relevant"]) for item in papers)
    year_violations = sum(not bool(item["year_ok"]) for item in papers)
    abstract_count = sum(bool(item["has_abstract"]) for item in papers)
    url_count = sum(bool(item["has_url"]) for item in papers)
    summary_count = sum(bool(item["has_summary"]) for item in papers)
    relevance_precision = relevant_count / count if count else 0.0
    return {
        "name": case["name"],
        "status": result.get("status"),
        "result_count": count,
        "relevant_count": relevant_count,
        "heuristic_relevance_precision": round(relevance_precision, 4),
        "year_from": year_from,
        "year_violation_count": year_violations,
        "abstract_coverage": round(abstract_count / count, 4) if count else 0.0,
        "url_coverage": round(url_count / count, 4) if count else 0.0,
        "summary_coverage": round(summary_count / count, 4) if count else 0.0,
        "contributing_sources": contributing_sources,
        "rate_limit_error_count": len(rate_limit_errors),
        "rate_limit_errors": rate_limit_errors,
        "passed": bool(
            count >= 5
            and relevance_precision >= 0.80
            and year_violations == 0
            and not rate_limit_errors
            and abstract_count == count
            and url_count == count
            and summary_count == count
        ),
        "papers": papers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year-from", type=int, default=2025)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=config.OUTPUT_DIR / "quality_benchmark")
    args = parser.parse_args()
    configure_utf8_console()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    audits = []
    for index, case in enumerate(CASES, 1):
        print(f"[{index}/{len(CASES)}] Running {case['name']}...", flush=True)
        result = run_pipeline(
            case["prompt"],
            search_depth="quick",
            result_limit=10,
            ai_rerank_limit=20,
            ai_enrich_limit=10,
            year_from_override=args.year_from,
            ranking_profile_override="latest",
            use_cache=not args.no_cache,
        )
        result_path = args.output_dir / f"{case['name']}.json"
        save_json(result, result_path)
        audit = audit_result(result, case, args.year_from)
        audit["result_file"] = str(result_path.resolve())
        audits.append(audit)
        print(
            f"  status={audit['status']} relevant={audit['relevant_count']}/{audit['result_count']} "
            f"year_errors={audit['year_violation_count']} rate_429={audit['rate_limit_error_count']}",
            flush=True,
        )

    report = {
        "benchmark_version": "1.0.0",
        "cache_disabled": bool(args.no_cache),
        "year_from": args.year_from,
        "case_count": len(audits),
        "passed_count": sum(bool(audit["passed"]) for audit in audits),
        "all_passed": all(bool(audit["passed"]) for audit in audits),
        "cases": audits,
    }
    report_path = args.output_dir / "quality_report.json"
    save_json(report, report_path)
    print(f"Saved report: {report_path.resolve()}", flush=True)
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
