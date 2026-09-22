#!/usr/bin/env python3
"""Aggregate stage-level ranking metrics across a benchmark manifest."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

from evaluate_results import evaluate


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(math.ceil(percentile * len(ordered)) - 1, len(ordered) - 1)
    return round(ordered[max(index, 0)], 6)


def _mean_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    names = sorted({
        key for row in rows for key, value in row.items()
        if isinstance(value, (int, float))
        and (key == "mrr" or key.startswith(("precision@", "recall@", "ndcg@")))
    })
    return {
        name: round(statistics.fmean(float(row[name]) for row in rows if name in row), 6)
        for name in names
    }


def evaluate_manifest(manifest_path: Path, ks: tuple[int, ...]) -> dict[str, Any]:
    manifest = _load(manifest_path)
    entries = manifest.get("queries") or []
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest.queries must be a non-empty array")
    base = manifest_path.parent
    per_query = []
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not entry.get("result") or not entry.get("labels"):
            raise ValueError(f"Invalid benchmark query at index {index}")
        result_path = (base / str(entry["result"])).resolve()
        labels_path = (base / str(entry["labels"])).resolve()
        result = _load(result_path)
        metrics = evaluate(result, _load(labels_path), ks)
        per_query.append({
            "name": entry.get("name") or f"query_{index}",
            "result": str(result_path),
            "metrics": metrics,
        })

    final_rows = [row["metrics"] for row in per_query]
    stage_names = sorted({
        name for row in final_rows for name in (row.get("stages") or {})
    })
    latencies = [
        float(row["system"]["latency_seconds"]) for row in final_rows
        if isinstance((row.get("system") or {}).get("latency_seconds"), (int, float))
    ]
    return {
        "query_count": len(per_query),
        "macro_average": _mean_metrics(final_rows),
        "stage_macro_average": {
            name: _mean_metrics([
                row["stages"][name] for row in final_rows if name in (row.get("stages") or {})
            ])
            for name in stage_names
        },
        "system": {
            "latency_p50_seconds": round(statistics.median(latencies), 6) if latencies else None,
            "latency_p95_seconds": _percentile(latencies, 0.95),
        },
        "per_query": per_query,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate an AI paper finder benchmark.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--k", type=int, nargs="+", default=[5, 10, 20])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if any(value <= 0 for value in args.k):
        parser.error("Every --k value must be positive")
    report = evaluate_manifest(args.manifest.resolve(), tuple(args.k))
    content = json.dumps(report, ensure_ascii=False, indent=2)
    print(content)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
