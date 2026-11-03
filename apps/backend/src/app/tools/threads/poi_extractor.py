"""Evidence-grounded POI extraction using Groq LLM and verification."""

import logging
from typing import Literal

from pydantic import BaseModel, Field

from app.tools.threads.ai import GroqThreadsAI
from app.tools.threads.comment_processing import (
    ConversationUnit,
    chunk_conversations,
    reconstruct_conversations,
)
from app.tools.threads.evidence_validator import (
    find_evidence_span,
    is_grounded_attribute,
)
from app.tools.threads.poi_schemas import POIClaim, POIMention
from app.tools.threads.schemas import ThreadsPost

logger = logging.getLogger(__name__)


class ExtractedClaimItem(BaseModel):
    claim_type: Literal[
        "location",
        "food",
        "price",
        "experience",
        "feature",
        "warning",
        "correction",
        "closure",
    ]
    value: str = Field(min_length=1, max_length=512)
    evidence_text: str = Field(min_length=1, max_length=2000)
    sentiment: Literal["positive", "neutral", "negative", "unknown"] = "unknown"


class ExtractedMentionItem(BaseModel):
    name_text: str = Field(min_length=1, max_length=256)
    category_text: str | None = None
    area_text: str | None = None
    address_text: str | None = None
    evidence_text: str = Field(min_length=1, max_length=2000)
    claims: list[ExtractedClaimItem] = Field(default_factory=list)


class ExtractionResponse(BaseModel):
    mentions: list[ExtractedMentionItem] = Field(default_factory=list)


_EXTRACTION_INSTRUCTION = (
    "You are an expert POI (Place of Interest) extraction assistant for social discussions. "
    "Given social conversations containing posts and community comments, extract all mentioned places, "
    "cafes, restaurants, food stalls, and scenic spots, along with specific claims made about them.\n"
    "CRITICAL GROUNDING RULES:\n"
    "1. Do NOT invent places, addresses, or attributes. The name_text and evidence_text MUST appear in the provided text.\n"
    "2. If full address or area is not explicitly stated in the source text, leave it as null. Never guess street numbers.\n"
    "3. Extract claims such as signature food, price levels, atmosphere, features, and warnings (e.g. 'đóng cửa rồi', 'rất đông').\n"
    "4. Negative sentiment or warnings (e.g. closure, bad service) MUST be preserved as claims with type 'warning' or 'closure'.\n"
    "5. Every claim must have an exact quote in evidence_text from the source.\n"
    "Return JSON matching the schema."
)


def _find_source_comment_id(unit: ConversationUnit, evidence_text: str) -> str | None:
    """Find which comment inside a conversation unit contains the evidence quote."""
    if unit.parent_comment and find_evidence_span(unit.parent_comment.text, evidence_text).is_valid:
        return unit.parent_comment.id
    for reply in unit.child_replies:
        if find_evidence_span(reply.text, evidence_text).is_valid:
            return reply.id
    return None


class POIExtractor:
    def __init__(self, ai: GroqThreadsAI) -> None:
        self.ai = ai

    async def extract_from_posts(
        self, posts: list[ThreadsPost]
    ) -> tuple[list[POIMention], list[POIClaim]]:
        all_units: list[ConversationUnit] = []
        for post in posts:
            all_units.extend(reconstruct_conversations(post))

        chunks = chunk_conversations(all_units, max_chunk_chars=3500)
        mentions: list[POIMention] = []
        claims: list[POIClaim] = []

        for chunk in chunks:
            rendered_texts = [u.render_context() for u in chunk]
            combined_text = "\n---\n".join(rendered_texts)
            if not combined_text.strip():
                continue

            try:
                response = await self.ai._complete(
                    _EXTRACTION_INSTRUCTION,
                    {"conversations": combined_text},
                    ExtractionResponse,
                )
            except Exception as exc:
                logger.warning("POI extraction chunk failed: %s", exc)
                continue

            for raw_mention in response.mentions:
                # Find matching unit in chunk that contains this mention's evidence
                matched_unit: ConversationUnit | None = None
                span_match = None
                for unit in chunk:
                    unit_rendered = unit.render_context()
                    match = find_evidence_span(unit_rendered, raw_mention.evidence_text)
                    if match.is_valid:
                        matched_unit = unit
                        span_match = match
                        break

                if matched_unit is None or span_match is None:
                    # Ungrounded mention hallucinated by LLM
                    continue

                source_post_id = matched_unit.post_id
                source_comment_id = _find_source_comment_id(matched_unit, raw_mention.evidence_text)

                # Validate attributes against source text; strip hallucinated values
                unit_text = matched_unit.render_context()
                grounded_area = (
                    raw_mention.area_text
                    if is_grounded_attribute(unit_text, raw_mention.area_text)
                    else None
                )
                grounded_addr = (
                    raw_mention.address_text
                    if is_grounded_attribute(unit_text, raw_mention.address_text)
                    else None
                )

                mention = POIMention(
                    name_text=raw_mention.name_text.strip(),
                    category_text=raw_mention.category_text,
                    area_text=grounded_area,
                    address_text=grounded_addr,
                    source_post_id=source_post_id,
                    source_comment_id=source_comment_id,
                    evidence_text=raw_mention.evidence_text.strip(),
                    start_offset=span_match.start_offset,
                    end_offset=span_match.end_offset,
                    context_incomplete=matched_unit.context_incomplete,
                )
                mentions.append(mention)

                for raw_claim in raw_mention.claims:
                    claim_match = find_evidence_span(unit_text, raw_claim.evidence_text)
                    if not claim_match.is_valid:
                        continue
                    claim_comment_id = _find_source_comment_id(matched_unit, raw_claim.evidence_text)
                    claims.append(
                        POIClaim(
                            mention_id=mention.id,
                            claim_type=raw_claim.claim_type,
                            value=raw_claim.value.strip(),
                            evidence_text=raw_claim.evidence_text.strip(),
                            source_post_id=source_post_id,
                            source_comment_id=claim_comment_id,
                            sentiment=raw_claim.sentiment,
                        )
                    )

        return mentions, claims
