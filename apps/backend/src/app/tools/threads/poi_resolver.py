"""Entity resolution for POI mentions into canonical POI candidates."""

import re
import unicodedata
from difflib import SequenceMatcher

from app.tools.threads.poi_schemas import POICandidate, POIClaim, POIMention

_COMMON_PREFIXES = [
    r"^(quán\s+ăn|quán|tiệm\s+bánh|tiệm|nhà\s+hàng|cà\s+phê|cafe)\s+",
]


def normalize_poi_name(name: str) -> str:
    """Normalize POI name for candidate clustering while keeping distinctive tokens."""
    if not name:
        return ""
    folded = unicodedata.normalize("NFC", name).casefold().strip()
    for prefix in _COMMON_PREFIXES:
        folded = re.sub(prefix, "", folded)
    return " ".join(folded.split())


def normalize_area(area: str | None) -> str:
    if not area:
        return ""
    return " ".join(unicodedata.normalize("NFC", area).casefold().split())


def compute_similarity(str1: str, str2: str) -> float:
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1, str2).ratio()


def are_distinct_branches(m1: POIMention, m2: POIMention) -> bool:
    """Check if two mentions explicitly refer to different branch locations."""
    a1 = normalize_area(m1.area_text or m1.address_text)
    a2 = normalize_area(m2.area_text or m2.address_text)
    if not a1 or not a2:
        return False
    # If both have explicit locations and similarity is low, treat as separate branches
    # Check if one is a substring of the other (e.g. "Hoàng Sa" in "725 Hoàng Sa, Q.3")
    return bool(compute_similarity(a1, a2) < 0.4 and (a1 not in a2 and a2 not in a1))


def resolve_poi_mentions(
    mentions: list[POIMention], claims: list[POIClaim]
) -> list[POICandidate]:
    """Cluster POI mentions into canonical candidates and attach claims."""
    if not mentions:
        return []

    claims_by_mention: dict[str, list[POIClaim]] = {}
    for claim in claims:
        claims_by_mention.setdefault(claim.mention_id, []).append(claim)

    candidates: list[POICandidate] = []

    for mention in mentions:
        norm_name = normalize_poi_name(mention.name_text)
        if not norm_name:
            continue

        matched_candidate: POICandidate | None = None

        for cand in candidates:
            cand_norm = normalize_poi_name(cand.canonical_name)
            sim = compute_similarity(norm_name, cand_norm)
            is_sub = (norm_name in cand_norm) or (cand_norm in norm_name)

            if sim >= 0.85 or (is_sub and sim >= 0.5):
                # Check for branch discrimination
                if any(are_distinct_branches(mention, existing) for existing in cand.mentions):
                    continue
                matched_candidate = cand
                break

        if matched_candidate is not None:
            # Merge mention into matched candidate
            matched_candidate.mentions.append(mention)
            # Pick more specific canonical name
            if len(mention.name_text) > len(matched_candidate.canonical_name):
                matched_candidate.canonical_name = mention.name_text
            # Fill missing attributes
            if not matched_candidate.category and mention.category_text:
                matched_candidate.category = mention.category_text
            if not matched_candidate.area and mention.area_text:
                matched_candidate.area = mention.area_text
            if not matched_candidate.address and mention.address_text:
                matched_candidate.address = mention.address_text
        else:
            candidates.append(
                POICandidate(
                    canonical_name=mention.name_text,
                    category=mention.category_text,
                    area=mention.area_text,
                    address=mention.address_text,
                    verification_status="candidate",
                    mentions=[mention],
                    claims=[],
                )
            )

    # Attach claims and evaluate verification status
    for cand in candidates:
        cand_claims: list[POIClaim] = []
        source_posts: set[str] = set()
        for m in cand.mentions:
            source_posts.add(m.source_post_id)
            cand_claims.extend(claims_by_mention.get(m.id, []))
        cand.claims = cand_claims
        cand.distinct_sources_count = len(source_posts)

        # Verification rule:
        # Requires at least 2 distinct source posts AND grounded location/address/area
        if cand.distinct_sources_count >= 2 and (cand.address or cand.area):
            cand.verification_status = "verified"
        elif not cand.canonical_name or len(cand.canonical_name.strip()) < 2:
            cand.verification_status = "unresolved"
        else:
            cand.verification_status = "candidate"

    return candidates
