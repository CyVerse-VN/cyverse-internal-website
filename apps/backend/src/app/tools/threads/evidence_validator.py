"""Evidence grounding and source text validation."""

import unicodedata
from typing import NamedTuple


class SpanMatch(NamedTuple):
    is_valid: bool
    start_offset: int | None
    end_offset: int | None


def normalize_for_matching(text: str) -> str:
    """Normalize whitespace and Unicode NFC for resilient matching."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def find_evidence_span(source_text: str, evidence_text: str) -> SpanMatch:
    """Verify that evidence_text is grounded in source_text and find exact offsets."""
    if not source_text or not evidence_text:
        return SpanMatch(False, None, None)

    source_norm = unicodedata.normalize("NFC", source_text)
    evidence_norm = unicodedata.normalize("NFC", evidence_text.strip())

    if not evidence_norm:
        return SpanMatch(False, None, None)

    # 1. Direct exact substring match
    idx = source_norm.find(evidence_norm)
    if idx != -1:
        return SpanMatch(True, idx, idx + len(evidence_norm))

    # 2. Case-insensitive match
    lower_source = source_norm.casefold()
    lower_ev = evidence_norm.casefold()
    idx = lower_source.find(lower_ev)
    if idx != -1:
        return SpanMatch(True, idx, idx + len(evidence_norm))

    # 3. Normalized whitespace match
    clean_ev = normalize_for_matching(evidence_norm)
    clean_src = normalize_for_matching(source_norm)
    if clean_ev.casefold() in clean_src.casefold():
        # Valid semantically, but exact byte offset in raw source is ambiguous
        return SpanMatch(True, None, None)

    return SpanMatch(False, None, None)


def is_grounded_attribute(source_text: str, attribute_value: str | None) -> bool:
    """Confirm whether an extracted attribute string actually originates in the source."""
    if not attribute_value or not attribute_value.strip():
        return False
    val = normalize_for_matching(attribute_value).casefold()
    src = normalize_for_matching(source_text).casefold()
    return val in src
