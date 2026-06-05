def has_public_evidence(candidate: dict) -> bool:
    return bool(str(candidate.get("evidence_note") or "").strip()) and bool(str(candidate.get("source_url") or "").strip())


def filter_candidates_with_evidence(candidates: list[dict]) -> list[dict]:
    return [candidate for candidate in candidates if has_public_evidence(candidate)]
