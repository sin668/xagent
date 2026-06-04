import hashlib
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models.enums import (
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    SourcePlatform,
)


@dataclass(frozen=True)
class LeadSourceCandidateDefaults:
    review_status: LeadSourceCandidateReviewStatus
    approved_for_extraction: bool
    extraction_status: LeadSourceCandidateExtractionStatus


class LeadSourceCandidateRules:
    @staticmethod
    def resolve_defaults(risk_level: ChannelRiskLevel | str) -> LeadSourceCandidateDefaults:
        risk = ChannelRiskLevel(risk_level)
        if risk in {ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM}:
            return LeadSourceCandidateDefaults(
                review_status=LeadSourceCandidateReviewStatus.AUTO_APPROVED,
                approved_for_extraction=True,
                extraction_status=LeadSourceCandidateExtractionStatus.PENDING,
            )
        if risk == ChannelRiskLevel.HIGH:
            return LeadSourceCandidateDefaults(
                review_status=LeadSourceCandidateReviewStatus.HIGH_RISK_REVIEW,
                approved_for_extraction=False,
                extraction_status=LeadSourceCandidateExtractionStatus.PENDING,
            )
        return LeadSourceCandidateDefaults(
            review_status=LeadSourceCandidateReviewStatus.REJECTED,
            approved_for_extraction=False,
            extraction_status=LeadSourceCandidateExtractionStatus.BLOCKED,
        )

    @staticmethod
    def normalize_url(url: str) -> str:
        parsed = urlsplit(url.strip())
        scheme = (parsed.scheme or "https").lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)
        return urlunsplit((scheme, netloc, path, query, ""))

    @classmethod
    def build_dedupe_key(
        cls,
        *,
        source_url: str,
        normalized_domain: str,
        platform: SourcePlatform | str,
    ) -> str:
        normalized = "|".join(
            [
                str(SourcePlatform(platform)),
                normalized_domain.strip().lower(),
                cls.normalize_url(source_url),
            ]
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
