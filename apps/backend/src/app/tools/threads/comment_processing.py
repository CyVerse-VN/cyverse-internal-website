"""Comment cleaning, deduplication and conversation context reconstruction."""

import re
import unicodedata
from dataclasses import dataclass, field

from app.tools.threads.schemas import ThreadsComment, ThreadsPost

_UI_NOISE_PATTERNS = [
    re.compile(r"^\s*Translate\s*$", re.IGNORECASE),
    re.compile(r"^\s*Dịch\s*$", re.IGNORECASE),
    re.compile(r"^\s*Reply\s*$", re.IGNORECASE),
    re.compile(r"^\s*Trả lời\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*(m|h|d|w|tháng|ngày|giờ|phút)\s*$", re.IGNORECASE),
]


def clean_comment_text(text: str) -> str:
    """Normalize whitespace and Unicode, and strip UI noise artifacts."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text)
    lines = [line.strip() for line in normalized.splitlines()]
    filtered = [
        line
        for line in lines
        if line and not any(pattern.match(line) for pattern in _UI_NOISE_PATTERNS)
    ]
    cleaned = " ".join(" ".join(filtered).split())
    return cleaned


def deduplicate_comments(comments: list[ThreadsComment]) -> list[ThreadsComment]:
    """Clean comments and merge DOM fallbacks that duplicate structured comments.

    Structured comments with verified IDs and parent links take precedence over
    DOM comments with identical normalized text. Different authors with similar
    content are preserved.
    """
    cleaned_comments: list[ThreadsComment] = []
    structured_by_key: dict[tuple[str, str], ThreadsComment] = {}

    for comment in comments:
        text = clean_comment_text(comment.text)
        if not text:
            continue
        cleaned = comment.model_copy(update={"text": text})
        cleaned_comments.append(cleaned)
        if comment.source == "structured":
            structured_by_key[(comment.username.lower(), text.casefold())] = cleaned

    results: list[ThreadsComment] = []
    for comment in cleaned_comments:
        if comment.source == "dom":
            match = structured_by_key.get((comment.username.lower(), comment.text.casefold()))
            if match is not None and match.id != comment.id:
                # Omit duplicate DOM fallback in favor of the structured record
                continue
        results.append(comment)

    return results


@dataclass
class ConversationUnit:
    """A self-contained conversation unit preserving parent-child context."""

    post_id: str
    post_text: str
    parent_comment: ThreadsComment | None = None
    child_replies: list[ThreadsComment] = field(default_factory=list)
    context_incomplete: bool = False

    def render_context(self) -> str:
        """Render conversation for extraction with explicit IDs for span grounding."""
        parts: list[str] = [f"[POST:{self.post_id}] {self.post_text}"]
        if self.parent_comment:
            parts.append(
                f"[COMMENT:{self.parent_comment.id} @{self.parent_comment.username}] {self.parent_comment.text}"
            )
        for reply in self.child_replies:
            reply_to = f" -> @{reply.reply_to_username}" if reply.reply_to_username else ""
            parts.append(
                f"[REPLY:{reply.id} @{reply.username}{reply_to}] {reply.text}"
            )
        return "\n".join(parts)


def reconstruct_conversations(post: ThreadsPost) -> list[ConversationUnit]:
    """Build conversation units preserving discussion threads.

    If comments have parent_id relations, they are linked to their parent.
    If parent is missing or unknown, marked context_incomplete.
    """
    cleaned = deduplicate_comments(post.comments)
    if not cleaned:
        return [
            ConversationUnit(
                post_id=post.post_id,
                post_text=post.text,
                parent_comment=None,
                child_replies=[],
                context_incomplete=False,
            )
        ]

    by_id: dict[str, ThreadsComment] = {c.id: c for c in cleaned}
    children_by_parent: dict[str, list[ThreadsComment]] = {}
    top_level: list[ThreadsComment] = []
    orphan_replies: list[ThreadsComment] = []

    for comment in cleaned:
        parent_id = comment.parent_id
        if parent_id and parent_id in by_id:
            children_by_parent.setdefault(parent_id, []).append(comment)
        elif parent_id and parent_id not in by_id:
            # Comment refers to a parent not present in collection
            orphan_replies.append(comment)
        else:
            top_level.append(comment)

    units: list[ConversationUnit] = []

    for parent in top_level:
        replies = children_by_parent.get(parent.id, [])
        units.append(
            ConversationUnit(
                post_id=post.post_id,
                post_text=post.text,
                parent_comment=parent,
                child_replies=replies,
                context_incomplete=False,
            )
        )

    for orphan in orphan_replies:
        units.append(
            ConversationUnit(
                post_id=post.post_id,
                post_text=post.text,
                parent_comment=orphan,
                child_replies=[],
                context_incomplete=True,
            )
        )

    return units


def chunk_conversations(
    units: list[ConversationUnit], max_chunk_chars: int = 4000
) -> list[list[ConversationUnit]]:
    """Group conversation units into chunks that stay within token limits."""
    chunks: list[list[ConversationUnit]] = []
    current_chunk: list[ConversationUnit] = []
    current_size = 0

    for unit in units:
        unit_size = len(unit.render_context())
        if current_chunk and current_size + unit_size > max_chunk_chars:
            chunks.append(current_chunk)
            current_chunk = [unit]
            current_size = unit_size
        else:
            current_chunk.append(unit)
            current_size += unit_size

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
