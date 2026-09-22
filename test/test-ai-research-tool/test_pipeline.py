from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import config
from academic_rate_limiter import request_interval_seconds, reset_rate_limiter, wait_for_source
from common import _retry_delay, normalize_date_vietnam, paper_record
from deduplicator import deduplicate_papers
from diversifier import diversify_ranked
from evaluate_results import evaluate
from filters import filter_papers, filter_ranked_by_relevance
from llm_cache import load_llm_cache, save_llm_cache
from llm_client import _groq_payload, _parse_mapping
from groq_rate_limiter import _duration_seconds
from paper_assessor import _validator_factory as assessment_validator_factory
from pipeline_cache import load_cached, save_cached
from query_builders import compile_source_queries
from query_planner import _apply_prompt_constraints, validate_query_plan
from ai_reranker import apply_ai_rerank
from ranker import rank_papers
from research_pipeline import _resolve_search_settings, _retrieve_source


def sample_paper(source: str, source_id: str, title: str, **values):
    defaults = {
        "source_name": source,
        "source_id": source_id,
        "source_rank": 1,
        "title": title,
        "abstract": "A sufficiently informative abstract.",
        "authors": ["Ada Lovelace"],
        "year": 2024,
        "published_at": "2024-01-01",
        "doi": "10.1234/example",
        "url": "https://example.org/paper",
        "pdf_url": "https://example.org/paper.pdf",
        "citation_count": 10,
        "reference_count": 20,
        "is_open_access": True,
        "fields": ["Artificial Intelligence"],
        "publication_types": ["article"],
        "source_specific": {},
    }
    defaults.update(values)
    return paper_record(**defaults)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.plan = validate_query_plan({
            "research_question": "RAG giảm hallucination trong y tế?",
            "english_question": "Does RAG reduce hallucination in medical LLMs?",
            "intent": "evidence_review",
            "ranking_profile": "evidence_review",
            "concept_groups": [
                {"concept": "retrieval augmented generation", "synonyms": ["RAG"], "required": True},
                {"concept": "hallucination", "synonyms": ["factuality"], "required": True},
            ],
            "filters": {
                "year_from": 2022,
                "year_to": None,
                "publication_types": ["article", "preprint"],
                "open_access_only": False,
                "languages": ["en"],
            },
            "query_variants": ["RAG hallucination medical LLM"],
        })

    def test_query_builders_keep_source_syntax_out_of_plan(self):
        compiled = compile_source_queries(self.plan)
        self.assertIn(" OR ", compiled["arxiv"][0]["query"])
        self.assertIn("submittedDate", compiled["arxiv"][0]["query"])
        self.assertIn(" AND ", compiled["openalex"][0]["query"])
        self.assertEqual(compiled["semantic_scholar"][0]["query"], "RAG hallucination medical LLM")
        self.assertNotIn("from_publication_date", compiled["openalex"][1]["filter"])
        self.assertIn("publication_year:>2021", compiled["openalex"][1]["filter"])

    def test_academic_source_rate_limits_include_safety_margin(self):
        self.assertEqual(request_interval_seconds("semantic_scholar"), 1.5)
        self.assertEqual(request_interval_seconds("arxiv"), 3.5)
        self.assertEqual(request_interval_seconds("openalex"), 1.5)

    def test_academic_rate_limiter_spaces_repeated_requests(self):
        reset_rate_limiter()
        with patch("academic_rate_limiter.time.monotonic", return_value=100.0), patch(
            "academic_rate_limiter.time.sleep"
        ) as sleep:
            self.assertEqual(wait_for_source("semantic_scholar"), 0.0)
            self.assertEqual(wait_for_source("semantic_scholar"), 1.5)
            sleep.assert_called_once_with(1.5)
        reset_rate_limiter()

    def test_retry_backoff_honors_header_and_adds_margin(self):
        self.assertEqual(_retry_delay({"Retry-After": "3"}, 1, 1.0), 3.5)
        self.assertEqual(_retry_delay({}, 2, 5.0), 10.5)

    def test_paper_dates_are_normalized_to_vietnam_calendar_date(self):
        self.assertEqual(normalize_date_vietnam("2026-09-10T18:30:00Z"), "2026-09-11")
        self.assertEqual(normalize_date_vietnam("2024-03-05"), "2024-03-05")
        self.assertIsNone(normalize_date_vietnam("not-a-date"))
        paper = sample_paper(
            "arxiv", "A-date", "Date normalization",
            year=None,
            published_at="2025-12-31T18:00:00+00:00",
            updated_at="01/01/2026",
        )
        self.assertEqual(paper["published_at"], "2026-01-01")
        self.assertEqual(paper["updated_at"], "2026-01-01")
        self.assertEqual(paper["year"], 2026)
        self.assertEqual(paper["schema_version"], "1.1.0")

    def test_prompt_since_year_overrides_model_exact_year(self):
        self.plan["filters"]["year_to"] = 2022
        corrected = _apply_prompt_constraints(self.plan, "Tìm paper từ năm 2022 về RAG")
        self.assertEqual(corrected["filters"]["year_from"], 2022)
        self.assertIsNone(corrected["filters"]["year_to"])

    def test_same_paper_merges_across_sources(self):
        left = sample_paper("arxiv", "2401.1", "A Useful RAG Study", arxiv_id="2401.00001")
        right = sample_paper("openalex", "W1", "A Useful RAG Study", arxiv_id="2401.00001")
        groups = deduplicate_papers([left, right])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["paper"]["source_specific"]["merged_sources"]), 2)

    def test_bad_title_does_not_merge_only_because_doi_matches(self):
        left = sample_paper("semantic_scholar", "S1", "Retrieval Augmented Generation Survey")
        right = sample_paper("openalex", "W1", "Unrelated Protein Folding Experiment")
        self.assertEqual(len(deduplicate_papers([left, right])), 2)

    def test_external_pubmed_id_merges_across_sources(self):
        left = sample_paper(
            "semantic_scholar", "S1", "Clinical Retrieval Augmented Generation",
            doi=None, source_specific={"external_ids": {"PubMed": "12345678"}},
        )
        right = sample_paper(
            "openalex", "W1", "Clinical Retrieval-Augmented Generation",
            doi=None,
            source_specific={"external_ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/12345678"}},
        )
        self.assertEqual(len(deduplicate_papers([left, right])), 1)

    def test_retracted_paper_is_filtered(self):
        paper = sample_paper("openalex", "W1", "Retracted Work", source_specific={"is_retracted": True})
        groups = deduplicate_papers([paper])
        kept, rejected = filter_papers(groups, self.plan["filters"], require_abstract=True)
        self.assertFalse(kept)
        self.assertEqual(rejected[0]["reason"], "retracted")

    def test_relevance_gate_rejects_off_topic_and_keeps_ai_supported_paper(self):
        irrelevant = {
            "dedup_key": "bad",
            "score_breakdown": {"text_match": 0.02},
            "ai_rerank": {
                "relevance": 0.05, "confidence": 0.95, "read_priority": "low"
            },
        }
        semantic_match = {
            "dedup_key": "good",
            "score_breakdown": {"text_match": 0.02},
            "ai_rerank": {
                "relevance": 0.85, "confidence": 0.80, "read_priority": "high"
            },
        }
        kept, rejected = filter_ranked_by_relevance([irrelevant, semantic_match])
        self.assertEqual([item["dedup_key"] for item in kept], ["good"])
        self.assertEqual(rejected[0]["reason"], "ai_high_confidence_irrelevant")

    def test_relevance_gate_does_not_fill_results_without_evidence(self):
        item = {
            "dedup_key": "weak",
            "score_breakdown": {"text_match": 0.05},
            "ai_rerank": None,
        }
        kept, rejected = filter_ranked_by_relevance([item])
        self.assertFalse(kept)
        self.assertEqual(rejected[0]["reason"], "insufficient_relevance_evidence")

    def test_relevance_gate_requires_all_required_concepts_unless_ai_overrides(self):
        partial = {
            "dedup_key": "partial",
            "score_breakdown": {
                "text_match": 0.50,
                "required_concept_coverage": 0.5,
            },
            "ai_rerank": {"relevance": 0.55, "confidence": 0.90},
        }
        supported = {
            "dedup_key": "supported",
            "score_breakdown": {
                "text_match": 0.10,
                "required_concept_coverage": 0.5,
            },
            "ai_rerank": {"relevance": 0.85, "confidence": 0.90},
        }
        kept, rejected = filter_ranked_by_relevance([partial, supported])
        self.assertEqual([item["dedup_key"] for item in kept], ["supported"])
        self.assertEqual(rejected[0]["reason"], "missing_required_concept")

    def test_ranker_returns_score_breakdown(self):
        paper = sample_paper("openalex", "W1", "Ranked Work")
        paper["source_specific"]["retrieval"] = {
            "source": "openalex", "mode": "lexical", "query": "rag", "rank": 1,
        }
        groups = deduplicate_papers([paper])
        ranked = rank_papers(groups, "balanced")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertIn("relevance", ranked[0]["score_breakdown"])

    def test_query_cache_round_trip(self):
        spec = {"mode": "lexical", "query": "RAG hallucination"}
        value = {"papers": [{"source_id": "W1"}], "total_available": 1}
        with TemporaryDirectory() as temporary_directory, patch.object(
            config, "QUERY_CACHE_DIR", Path(temporary_directory)
        ), patch.object(config, "ENABLE_QUERY_CACHE", True), patch.object(
            config, "QUERY_CACHE_TTL_SECONDS", 60
        ):
            self.assertIsNone(load_cached("openalex", spec, 10))
            save_cached("openalex", spec, 10, value)
            self.assertEqual(load_cached("openalex", spec, 10), value)

    def test_llm_cache_round_trip(self):
        identity = {"tool_name": "test", "prompt": "hello"}
        value = {"value": {"ok": True}, "requested_model": "a", "response_model": "b"}
        with TemporaryDirectory() as temporary_directory, patch.object(
            config, "LLM_CACHE_DIR", Path(temporary_directory)
        ), patch.object(config, "ENABLE_LLM_CACHE", True), patch.object(
            config, "LLM_CACHE_TTL_SECONDS", 60
        ):
            self.assertIsNone(load_llm_cache(identity))
            save_llm_cache(identity, value)
            self.assertEqual(load_llm_cache(identity), value)

    def test_llm_parser_accepts_safe_python_style_mapping(self):
        self.assertEqual(_parse_mapping("{'rerankings': []}"), {"rerankings": []})
        with self.assertRaises(ValueError):
            _parse_mapping("__import__('os').system('echo unsafe')")

    def test_assessment_requires_vietnamese_summary_and_why_read(self):
        paper_id = "doi:10.1234/test"
        valid = {
            "assessments": [{
                "paper_id": paper_id,
                "summary": "Bài báo đề xuất một phương pháp phát hiện nội dung giả mạo.",
                "main_contribution": "Đóng góp chính là mô hình phát hiện có khả năng tổng quát hóa.",
                "why_read": "Nên đọc để hiểu phương pháp và các giới hạn được báo cáo.",
                "paper_type": "method",
                "tags": ["phát hiện deepfake"],
                "evidence_strength": "0.8",
                "limitations_visible_from_abstract": [],
                "confidence": 0.9,
            }]
        }
        result = assessment_validator_factory({paper_id})(valid)
        self.assertEqual(result["assessments"][0]["evidence_strength"], 0.8)
        invalid = {"assessments": [{**valid["assessments"][0], "summary": "English summary only."}]}
        with self.assertRaises(ValueError):
            assessment_validator_factory({paper_id})(invalid)

    def test_groq_payload_uses_strict_schema_for_gpt_oss(self):
        payload = _groq_payload(
            model="openai/gpt-oss-20b",
            tool_name="test_tool",
            tool_description="test",
            parameters={"type": "object", "additionalProperties": False, "properties": {}},
            system_prompt="Return data.",
            user_prompt="input",
            max_tokens=500,
        )
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])
        self.assertEqual(payload["reasoning_effort"], "low")
        self.assertNotIn("tools", payload)
        contract = payload["messages"][0]["content"]
        self.assertIn("MANDATORY OUTPUT CONTRACT", contract)
        self.assertIn("no Markdown", contract)
        self.assertIn("Exact JSON Schema", contract)

    def test_retry_configuration_means_initial_request_plus_one_retry(self):
        self.assertEqual(config.REQUEST_ATTEMPTS, 2)
        self.assertEqual(config.LLM_ATTEMPTS, 2)

    def test_groq_duration_header_parser(self):
        self.assertAlmostEqual(_duration_seconds("2m59.56s"), 179.56)
        self.assertEqual(_duration_seconds("7.66s"), 7.66)

    def test_source_fusion_uses_best_rank_once_per_source(self):
        s2 = sample_paper("semantic_scholar", "S1", "RAG hallucination medical LLM")
        s2["source_specific"]["retrieval_hits"] = [
            {"source": "semantic_scholar", "mode": "lexical", "query": f"q{i}", "rank": i}
            for i in (1, 2, 3)
        ]
        arxiv = sample_paper("arxiv", "A1", "RAG hallucination medical LLM")
        arxiv["source_specific"]["retrieval_hits"] = [
            {"source": "arxiv", "mode": "boolean", "query": "q", "rank": 1}
        ]
        ranked = rank_papers([
            {"dedup_key": "s2", "paper": s2},
            {"dedup_key": "arxiv", "paper": arxiv},
        ], "balanced", self.plan)
        by_id = {item["dedup_key"]: item for item in ranked}
        self.assertEqual(by_id["s2"]["score_breakdown"]["source_rrf"], 1.0)
        self.assertEqual(by_id["arxiv"]["score_breakdown"]["source_rrf"], 1.0)
        self.assertEqual(by_id["s2"]["score_breakdown"]["source_agreement"], 0.333333)

    def test_ai_rerank_changes_query_match_not_paper_quality(self):
        paper = sample_paper("openalex", "W1", "RAG medical hallucination")
        ranked = rank_papers([{"dedup_key": "one", "paper": paper}], "balanced", self.plan)
        before_quality = ranked[0]["paper_quality_score"]
        result = apply_ai_rerank(ranked, {
            "one": {
                "relevance": 0.1, "intent_match": 0.2, "method_match": 0.3,
                "confidence": 1.0, "reason": "Limited match",
            }
        }, "balanced")
        self.assertEqual(result[0]["paper_quality_score"], before_quality)
        self.assertNotEqual(result[0]["query_match_score"], result[0]["deterministic_query_match_score"])

    def test_low_confidence_ai_score_is_ignored(self):
        paper = sample_paper("openalex", "W1", "RAG medical hallucination")
        ranked = rank_papers([{"dedup_key": "one", "paper": paper}], "balanced", self.plan)
        result = apply_ai_rerank(ranked, {
            "one": {
                "relevance": 0.0, "intent_match": 0.0, "method_match": 0.0,
                "confidence": 0.1, "reason": "Uncertain",
            }
        }, "balanced")
        self.assertEqual(result[0]["query_match_score"], result[0]["deterministic_query_match_score"])
        self.assertEqual(result[0]["score_breakdown"]["ai_ignored_low_confidence"], 1.0)

    def test_search_depth_presets_and_overrides(self):
        quick = _resolve_search_settings("quick", None, None, None, None, None, None, None)
        standard = _resolve_search_settings("standard", None, None, None, None, None, None, None)
        custom = _resolve_search_settings(
            "quick", {"arxiv": 12}, None, 77, None, None, None, None
        )
        self.assertLess(quick["max_candidates"], standard["max_candidates"])
        self.assertEqual(custom["request_limits"]["arxiv"], 12)
        self.assertEqual(custom["max_candidates"], 77)
        self.assertTrue(all(
            weights["source_agreement"] <= 0.03
            for weights in config.PAPER_QUALITY_WEIGHTS.values()
        ))

    def test_adaptive_retrieval_skips_unneeded_query_variant(self):
        specs = [
            {"mode": "relevance", "query": "q1"},
            {"mode": "relevance", "query": "q2"},
            {"mode": "relevance", "query": "q3"},
        ]
        responses = [
            {"papers": [{"source_id": f"S{i}", "source_rank": i + 1, "source_specific": {}} for i in range(4)]},
            {"papers": [{"source_id": f"S{i}", "source_rank": i + 1, "source_specific": {}} for i in range(4, 8)]},
        ]
        with patch("research_pipeline.search_semantic_scholar", side_effect=responses) as search, patch(
            "research_pipeline.time.sleep"
        ):
            result = _retrieve_source(
                "semantic_scholar", specs,
                {"semantic_scholar": 4, "arxiv": 4, "openalex_lexical": 4, "openalex_semantic": 4},
                10, 5.0, False, True,
            )
        self.assertEqual(search.call_count, 2)
        self.assertTrue(result["adaptive"]["stopped_early"])
        self.assertEqual(result["requests"][-1]["skip_reason"], "source_target_reached")

    def test_diversity_can_promote_a_different_topic(self):
        def ranked_item(key: str, title: str, score: float):
            return {
                "dedup_key": key, "rank": 1, "score": score,
                "recommendation_score": score,
                "paper": {"title": title, "abstract": title},
            }
        values = [
            ranked_item("a", "RAG medical hallucination evaluation benchmark", 1.0),
            ranked_item("b", "RAG medical hallucination evaluation benchmark study", 0.99),
            ranked_item("c", "RAG citation attribution knowledge grounding", 0.95),
        ]
        with patch.object(config, "DIVERSITY_LAMBDA", 0.5):
            result = diversify_ranked(values, 2, enabled=True)
        self.assertEqual([item["dedup_key"] for item in result], ["a", "c"])

    def test_evaluation_metrics(self):
        result = {
            "papers": [{"dedup_key": "a"}, {"dedup_key": "b"}],
            "stage_rankings": {"deterministic": ["b", "a"], "final_diversified": ["a", "b"]},
            "metrics": {"duplicate_rate": 0.2},
        }
        metrics = evaluate(result, {"relevance_grades": {"a": 3, "b": 0, "c": 2}}, (1, 2))
        self.assertEqual(metrics["precision@1"], 1.0)
        self.assertEqual(metrics["recall@2"], 0.5)
        self.assertEqual(metrics["mrr"], 1.0)
        self.assertEqual(metrics["stages"]["deterministic"]["mrr"], 0.5)


if __name__ == "__main__":
    unittest.main()
