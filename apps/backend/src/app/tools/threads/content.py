"""Conservative cleanup for text extracted from page UI, never structured captions."""

import re

DOM_LABELS = frozenset({"Author", "Follow", "Reply", "Translate", "See translation", "·"})
DOM_TIMESTAMP = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}|\d+\s*[smhdwy]", re.IGNORECASE)
LEGACY_WRAPPED_TEXT = re.compile(
    r"^\d{1,2}/\d{1,2}/\d{2,4}\s+(.+?)\s+(?:Translate|See translation)\s*$", re.DOTALL
)


def dom_comment_text(username: str, fragments: list[str]) -> str:
    content: list[str] = []
    for fragment in fragments:
        value = fragment.strip()
        if not value or value == username or value in DOM_LABELS or DOM_TIMESTAMP.fullmatch(value):
            continue
        content.append(value)
    return "\n".join(content)


def clean_stored_comment(data: dict[str, object]) -> dict[str, object]:
    identifier, text = data.get("id"), data.get("text")
    if isinstance(identifier, str) and identifier.startswith("dom_") and isinstance(text, str):
        matched = LEGACY_WRAPPED_TEXT.fullmatch(text.strip())
        if matched:
            return {**data, "text": matched.group(1)}
    return data
