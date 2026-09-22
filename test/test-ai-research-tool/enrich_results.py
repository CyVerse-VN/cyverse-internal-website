#!/usr/bin/env python3
"""Re-run Vietnamese AI enrichment on an existing pipeline result without new paper API calls."""

from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path
from typing import Any

import config
from common import configure_utf8_console, save_json
from paper_assessor import assess_ranked_papers
from research_pipeline import _result_assessment


def _usage(meta: dict[str, Any]) -> dict[str, float]:
    rows = [row for row in meta.get("usage_by_batch") or [] if not row.get("cached")]
    return {
        key: round(sum(float(row.get(key) or 0) for row in rows), 8)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost")
    }


def enrich_file(input_path: Path, output_path: Path, limit: int | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    data = json.loads(input_path.read_text(encoding="utf-8"))
    papers = data.get("papers")
    if not isinstance(papers, list) or not papers:
        raise ValueError("File không có papers để enrich")
    maximum = min(limit or len(papers), len(papers))
    plan = data.get("query_plan") or {}
    question = plan.get("english_question") or plan.get("research_question") or data.get("prompt")
    assessments, meta = assess_ranked_papers(question, papers, use_ai=True, limit=maximum)

    result = copy.deepcopy(data)
    result["pipeline_version"] = "2.2.0"
    result["llm_provider"] = config.llm_provider()
    result["model"] = config.llm_primary_model("enrich_papers")
    result["papers"] = [
        {
            **item,
            "assessment": _result_assessment(item, assessments.get(item["dedup_key"])),
        }
        for item in papers
    ]
    result["assessor"] = meta
    metrics = result.setdefault("metrics", {})
    degraded = [name for name in metrics.get("degraded_components") or [] if name != "ai_enrichment"]
    if meta.get("paper_count", 0) < maximum:
        degraded.append("ai_enrichment")
    metrics["degraded_components"] = degraded
    metrics["reenrichment_llm_usage_current_run"] = _usage(meta)
    result.setdefault("timings_seconds", {})["ai_reenrichment"] = round(
        time.perf_counter() - started, 3
    )
    source_errors = int(metrics.get("source_error_count") or 0)
    result["status"] = "partial_success" if source_errors or degraded else "success"
    save_json(result, output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-enrich final papers with Vietnamese output from the configured LLM provider."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit phải lớn hơn 0")
    output = args.output or args.input.with_name(f"{args.input.stem}_vi{args.input.suffix}")
    result = enrich_file(args.input, output, args.limit)
    assessor = result["assessor"]
    print(
        f"Vietnamese enrichment: {assessor.get('paper_count', 0)}/"
        f"{assessor.get('expected_paper_count', 0)} papers; saved: {output.resolve()}"
    )
    return 0 if assessor.get("paper_count") == assessor.get("expected_paper_count") else 1


if __name__ == "__main__":
    configure_utf8_console()
    raise SystemExit(main())
