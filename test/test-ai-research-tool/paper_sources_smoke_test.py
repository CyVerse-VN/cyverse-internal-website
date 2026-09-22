#!/usr/bin/env python3
"""Chạy lần lượt cả ba nguồn. Có thể test riêng bằng ba file *_test.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import config
from arxiv_test import search as search_arxiv
from common import configure_utf8_console, execute_source, save_json, validate_args
from openalex_test import search as search_openalex
from semantic_scholar_test import search as search_semantic_scholar


SEARCHERS = {
    "semantic_scholar": search_semantic_scholar,
    "arxiv": search_arxiv,
    "openalex": search_openalex,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test lần lượt Semantic Scholar, arXiv và OpenAlex.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("query", nargs="?", default=config.DEFAULT_QUERY)
    parser.add_argument("--limit", type=int, default=config.DEFAULT_LIMIT)
    parser.add_argument("--timeout", type=float, default=config.DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    validate_args(parser, args)

    sources = {}
    exit_code = 0
    for name, searcher in SEARCHERS.items():
        result, source_exit_code = execute_source(name, searcher, args.query, args.limit, args.timeout)
        sources[name] = result
        exit_code = max(exit_code, source_exit_code)

    papers = [
        paper
        for source_result in sources.values()
        for paper in source_result.get("papers", [])
    ]
    source_status = {
        name: {key: value for key, value in source_result.items() if key != "papers"}
        for name, source_result in sources.items()
    }
    payload = {
        "schema_version": config.PAPER_SCHEMA_VERSION,
        "query": args.query,
        "limit_per_source": args.limit,
        "paper_count": len(papers),
        "papers": papers,
        "sources": source_status,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    should_save = not args.no_save and (config.SAVE_RESULTS_BY_DEFAULT or args.output is not None)
    if should_save:
        output_path = args.output or config.OUTPUT_DIR / "all_sources.json"
        save_json(payload, output_path)
        print(f"Đã lưu: {output_path.resolve()}")
    return exit_code


if __name__ == "__main__":
    configure_utf8_console()
    raise SystemExit(main())
