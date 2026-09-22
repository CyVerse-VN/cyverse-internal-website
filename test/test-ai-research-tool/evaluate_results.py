#!/usr/bin/env python3
"""Evaluate a saved ranking with human relevance grades (0-3)."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _paper_id(item: dict[str, Any]) -> str:
    paper = item.get("paper") or {}
    return str(
        item.get("dedup_key") or paper.get("doi") or paper.get("arxiv_id")
        or f"{paper.get('source')}:{paper.get('source_id')}"
    )


def _evaluate_ranking(
    ranked_ids: list[str], normalized: dict[str, float], ks: tuple[int, ...]
) -> dict[str, Any]:
    total_relevant = sum(value > 0 for value in normalized.values())
    metrics: dict[str, Any] = {}
    first_relevant_rank = next(
        (index for index, paper_id in enumerate(ranked_ids, 1) if normalized.get(paper_id, 0) > 0),
        None,
    )
    metrics["mrr"] = round(1.0 / first_relevant_rank, 6) if first_relevant_rank else 0.0

    for k in sorted(set(ks)):
        ids = ranked_ids[:k]
        relevant_found = sum(normalized.get(paper_id, 0) > 0 for paper_id in ids)
        precision = relevant_found / len(ids) if ids else 0.0
        recall = relevant_found / total_relevant if total_relevant else 0.0
        dcg = sum(
            (2 ** normalized.get(paper_id, 0) - 1) / math.log2(rank + 1)
            for rank, paper_id in enumerate(ids, 1)
        )
        ideal = sorted(normalized.values(), reverse=True)[:k]
        idcg = sum((2 ** grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal, 1))
        metrics[f"precision@{k}"] = round(precision, 6)
        metrics[f"recall@{k}"] = round(recall, 6)
        metrics[f"ndcg@{k}"] = round(dcg / idcg, 6) if idcg else 0.0

    metrics["ranking_size"] = len(ranked_ids)
    metrics["judged_in_ranking"] = sum(paper_id in normalized for paper_id in ranked_ids)
    return metrics


def evaluate(result: dict[str, Any], labels: dict[str, Any], ks: tuple[int, ...]) -> dict[str, Any]:
    grades = labels.get("relevance_grades") or {}
    if not isinstance(grades, dict):
        raise ValueError("labels.relevance_grades must be an object mapping paper_id to grade 0-3")
    normalized = {str(key): max(0.0, min(float(value), 3.0)) for key, value in grades.items()}
    final_ids = [_paper_id(item) for item in result.get("papers") or []]
    metrics = _evaluate_ranking(final_ids, normalized, ks)
    metrics["labeled_papers"] = len(normalized)
    metrics["relevant_labeled_papers"] = sum(value > 0 for value in normalized.values())
    metrics["duplicate_rate_from_pipeline"] = (result.get("metrics") or {}).get("duplicate_rate")
    stage_rankings = result.get("stage_rankings") or {}
    if isinstance(stage_rankings, dict):
        metrics["stages"] = {
            str(name): _evaluate_ranking(
                [str(paper_id) for paper_id in paper_ids], normalized, ks
            )
            for name, paper_ids in stage_rankings.items()
            if isinstance(paper_ids, list)
        }
    timings = result.get("timings_seconds") or {}
    metrics["system"] = {
        "latency_seconds": result.get("elapsed_seconds"),
        "stage_timings_seconds": timings,
        "source_error_count": (result.get("metrics") or {}).get("source_error_count"),
    }
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a research_pipeline JSON against human labels.")
    parser.add_argument("result", type=Path)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--k", type=int, nargs="+", default=[5, 10, 20])
    args = parser.parse_args()
    if any(value <= 0 for value in args.k):
        parser.error("Every --k value must be positive")
    metrics = evaluate(_load(args.result), _load(args.labels), tuple(args.k))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
