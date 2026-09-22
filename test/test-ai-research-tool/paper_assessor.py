"""AI enrichment for the final shortlist; it never changes ranking or metadata."""

from __future__ import annotations

import json
import re
from typing import Any

import config
from common import SourceError, compact_text
from llm_client import call_tool


PAPER_TYPES = {
    "method", "review", "survey", "benchmark", "dataset", "application", "theory", "other",
}
VIETNAMESE_DIACRITICS = re.compile(
    r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
    flags=re.I,
)


def _require_vietnamese(label: str, value: str) -> None:
    # Vietnamese technical prose normally contains multiple diacritics. Requiring them rejects
    # English responses while still allowing English model/dataset names inside Vietnamese text.
    if len(VIETNAMESE_DIACRITICS.findall(value)) < 2:
        raise ValueError(f"{label} phải được viết bằng tiếng Việt có dấu")


def _score(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Assessment score must be a number")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Assessment score must be a number") from exc
    return round(max(0.0, min(numeric, 1.0)), 4)


def _validator_factory(allowed_ids: set[str]):
    def validate(value: dict[str, Any]) -> dict[str, Any]:
        rows = value.get("assessments")
        if not isinstance(rows, list):
            raise ValueError("assessments must be an array")
        assessments = []
        seen = set()
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            paper_id = compact_text(raw.get("paper_id"))
            if not paper_id or paper_id not in allowed_ids or paper_id in seen:
                continue
            paper_type = raw.get("paper_type")
            if paper_type not in PAPER_TYPES:
                raise ValueError("Invalid paper_type")
            summary = compact_text(raw.get("summary"))
            contribution = compact_text(raw.get("main_contribution"))
            why_read = compact_text(raw.get("why_read"))
            if not summary or not contribution or not why_read:
                raise ValueError("Missing summary/main_contribution/why_read")
            _require_vietnamese("summary", summary)
            _require_vietnamese("main_contribution", contribution)
            _require_vietnamese("why_read", why_read)
            limitations = [
                text for item in raw.get("limitations_visible_from_abstract") or []
                if (text := compact_text(item))
            ]
            tags = [text for item in raw.get("tags") or [] if (text := compact_text(item))]
            assessments.append({
                "paper_id": paper_id,
                "summary": summary,
                "main_contribution": contribution,
                "why_read": why_read,
                "paper_type": paper_type,
                "tags": list(dict.fromkeys(tags))[:6],
                "evidence_strength": _score(raw.get("evidence_strength")),
                "limitations_visible_from_abstract": limitations[:5],
                "confidence": _score(raw.get("confidence")),
                "evidence_scope": "abstract",
            })
            seen.add(paper_id)
        if seen != allowed_ids:
            missing = sorted(allowed_ids - seen)
            raise ValueError(f"Model thiếu {len(missing)} paper assessment")
        return {"assessments": assessments}
    return validate


def assess_ranked_papers(
    question: str,
    ranked: list[dict[str, Any]],
    *,
    use_ai: bool = True,
    limit: int | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    shortlist = ranked[:limit or config.AI_ENRICH_LIMIT]
    if not shortlist or not use_ai or not config.llm_api_key():
        reason = "no_papers" if not shortlist else "ai_disabled" if not use_ai else "missing_llm_api_key"
        return {}, {"used_ai": False, "fallback_reason": reason, "paper_count": 0}

    schema = json.loads((config.BASE_DIR / "paper_assessment.schema.json").read_text(encoding="utf-8"))
    parameters = {key: value for key, value in schema.items() if key not in {"$schema", "$id", "title"}}
    all_assessments: dict[str, dict[str, Any]] = {}
    selected_models = []
    response_models = []
    attempted_models_by_batch = []
    model_errors_by_batch = []
    rate_limit_wait_by_batch = []
    usage_by_batch = []
    errors = []
    cached_batches = 0
    batch_size = max(int(config.AI_ENRICH_BATCH_SIZE), 1)
    for start in range(0, len(shortlist), batch_size):
        batch = shortlist[start:start + batch_size]
        # Citation count and venue are deliberately omitted to reduce prestige bias.
        candidates = [{
            "paper_id": item["dedup_key"],
            "title": item["paper"].get("title"),
            "abstract": (item["paper"].get("abstract") or "")[:config.AI_ENRICH_ABSTRACT_MAX_CHARS],
            "publication_types": item["paper"].get("publication_types") or [],
            "final_rank": item["rank"],
        } for item in batch]
        allowed_ids = {item["paper_id"] for item in candidates}
        try:
            result = call_tool(
                tool_name="enrich_papers",
                tool_description=(
                    "Tóm tắt paper và giải thích bằng tiếng Việt vì sao paper đáng đọc cho câu hỏi nghiên cứu."
                ),
                parameters=parameters,
                system_prompt=(
                    "Bạn phân tích paper học thuật chỉ từ title, abstract và publication type được cung cấp. "
                    "BẮT BUỘC viết summary, main_contribution, why_read, tags và limitations bằng tiếng Việt có dấu. "
                    "Output tiếng Anh hoặc tiếng Việt không dấu sẽ bị từ chối. "
                    "Mỗi summary tối đa 2 câu ngắn; main_contribution và why_read mỗi field tối đa 1 câu. "
                    "Mỗi paper chỉ tạo tối đa 4 tags và 2 limitations. "
                    "Summary và main_contribution phải phản ánh paper, không điều chỉnh theo câu hỏi tìm kiếm; "
                    "riêng why_read phải giải thích ngắn gọn paper hữu ích thế nào cho research_question. "
                    "Không bịa kết quả, phương pháp, trạng thái phản biện hay hạn chế không thấy trong abstract. "
                    "Nếu bằng chứng trong abstract yếu, phải giảm confidence và nói thận trọng."
                ),
                user_prompt=json.dumps({
                    "research_question": question,
                    "output_language": "vi-VN",
                    "papers": candidates,
                }, ensure_ascii=False),
                validator=_validator_factory(allowed_ids),
                max_tokens=3500,
            )
        except SourceError as exc:
            errors.append({"batch_start": start, "error": str(exc)})
            break
        selected_models.append(result.requested_model)
        response_models.append(result.response_model)
        attempted_models_by_batch.append(list(result.attempted_models))
        model_errors_by_batch.append(list(result.model_errors))
        rate_limit_wait_by_batch.append(result.rate_limit_wait_seconds)
        cached_batches += int(result.cached)
        usage_by_batch.append({"cached": result.cached, **result.usage})
        for item in result.value["assessments"]:
            all_assessments[item["paper_id"]] = {
                key: value for key, value in item.items() if key != "paper_id"
            }

    expected_count = len(shortlist)
    primary_model = config.llm_primary_model("enrich_papers")
    return all_assessments, {
        "used_ai": bool(all_assessments),
        "provider": config.llm_provider(),
        "requested_model": primary_model,
        "selected_models": list(dict.fromkeys(selected_models)),
        "models": list(dict.fromkeys(response_models)),
        "fallback_model_used": any(model != primary_model for model in selected_models),
        "paper_count": len(all_assessments),
        "expected_paper_count": expected_count,
        "batch_count": (expected_count + batch_size - 1) // batch_size,
        "completed_batch_count": len(usage_by_batch),
        "cached_batches": cached_batches,
        "usage_by_batch": usage_by_batch,
        "attempted_models_by_batch": attempted_models_by_batch,
        "model_errors_by_batch": model_errors_by_batch,
        "rate_limit_wait_by_batch": rate_limit_wait_by_batch,
        "stopped_after_exhausting_models": bool(errors),
        "errors": errors,
    }
