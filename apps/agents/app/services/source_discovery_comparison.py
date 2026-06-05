from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit


class SourceDiscoveryShadowComparisonService:
    schema_version = "phase4.source_discovery.shadow_comparison.v1"

    def compare(self, existing_results: list[dict[str, Any]], shadow_output: dict[str, Any]) -> dict[str, Any]:
        self._ensure_shadow_output_is_read_only(shadow_output)

        existing_by_url = {
            self.normalize_url(str(item.get("normalized_url") or item.get("source_url") or item.get("url") or "")): item
            for item in existing_results
            if self.normalize_url(str(item.get("normalized_url") or item.get("source_url") or item.get("url") or ""))
        }
        shadow_candidates = list(shadow_output.get("candidates") or [])
        shadow_by_url = {
            self.normalize_url(str(item.get("normalized_url") or item.get("source_url") or item.get("url") or "")): item
            for item in shadow_candidates
            if self.normalize_url(str(item.get("normalized_url") or item.get("source_url") or item.get("url") or ""))
        }

        existing_urls = set(existing_by_url)
        shadow_urls = set(shadow_by_url)
        matched_urls = sorted(existing_urls & shadow_urls)
        added_urls = sorted(shadow_urls - existing_urls)
        missing_urls = sorted(existing_urls - shadow_urls)

        added = [
            {
                "normalized_url": url,
                "shadow_url": str(shadow_by_url[url].get("url") or shadow_by_url[url].get("source_url") or ""),
                "shadow_risk_level": self.normalize_risk(shadow_by_url[url].get("risk_level")),
            }
            for url in added_urls
        ]
        missing = [
            {
                "normalized_url": url,
                "existing_url": str(existing_by_url[url].get("source_url") or existing_by_url[url].get("url") or ""),
                "existing_risk_level": self.normalize_risk(existing_by_url[url].get("risk_level")),
            }
            for url in missing_urls
        ]

        risk_differences = []
        evidence_differences = []
        for url in matched_urls:
            existing = existing_by_url[url]
            shadow = shadow_by_url[url]
            existing_risk = self.normalize_risk(existing.get("risk_level"))
            shadow_risk = self.normalize_risk(shadow.get("risk_level"))
            if existing_risk != shadow_risk:
                risk_differences.append(
                    {
                        "normalized_url": url,
                        "existing_risk_level": existing_risk,
                        "shadow_risk_level": shadow_risk,
                    }
                )

            existing_has_evidence = self.has_evidence(existing)
            shadow_has_evidence = self.has_evidence(shadow)
            if existing_has_evidence != shadow_has_evidence:
                evidence_differences.append(
                    {
                        "normalized_url": url,
                        "existing_has_evidence": existing_has_evidence,
                        "shadow_has_evidence": shadow_has_evidence,
                    }
                )

        blocking_risks = [
            {
                "risk_type": "forbidden_leak",
                "normalized_url": url,
                "shadow_url": str(item.get("url") or item.get("source_url") or ""),
                "message": "Forbidden 来源出现在 shadow 有效候选中，禁止进入 active_run。",
            }
            for url, item in sorted(shadow_by_url.items())
            if self.normalize_risk(item.get("risk_level")) == "forbidden"
        ]

        return {
            "schema_version": self.schema_version,
            "writes_business_tables": False,
            "metrics": {
                "existing_count": len(existing_by_url),
                "shadow_count": len(shadow_by_url),
                "matched_count": len(matched_urls),
                "added_count": len(added),
                "missing_count": len(missing),
                "risk_difference_count": len(risk_differences),
                "evidence_difference_count": len(evidence_differences),
                "forbidden_leak_count": len(blocking_risks),
            },
            "added": added,
            "missing": missing,
            "risk_differences": risk_differences,
            "evidence_differences": evidence_differences,
            "blocking_risks": blocking_risks,
        }

    @staticmethod
    def _ensure_shadow_output_is_read_only(shadow_output: dict[str, Any]) -> None:
        audit = shadow_output.get("audit") if isinstance(shadow_output.get("audit"), dict) else {}
        written_tables = set(audit.get("written_tables") or [])
        if audit.get("writes_core_tables") is True or "lead_source_candidates" in written_tables:
            raise ValueError("Source Discovery shadow 对照不得写业务表。")

    @classmethod
    def has_evidence(cls, item: dict[str, Any]) -> bool:
        evidence_values = [
            item.get("evidence_summary"),
            item.get("evidence_note"),
            item.get("discovery_reason"),
        ]
        evidence_links = item.get("evidence_links")
        return any(str(value or "").strip() for value in evidence_values) or bool(evidence_links)

    @staticmethod
    def normalize_risk(value: Any) -> str:
        risk = str(value or "unknown").strip().lower()
        mapping = {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "forbidden": "forbidden",
            "watch": "medium",
            "allowed": "low",
        }
        return mapping.get(risk, risk)

    @staticmethod
    def normalize_url(url: str) -> str:
        stripped = url.strip()
        if not stripped:
            return ""
        if "://" not in stripped:
            stripped = f"https://{stripped}"
        parts = urlsplit(stripped)
        scheme = (parts.scheme or "https").lower()
        netloc = parts.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parts.path.rstrip("/")
        return urlunsplit((scheme, netloc, path, "", ""))
