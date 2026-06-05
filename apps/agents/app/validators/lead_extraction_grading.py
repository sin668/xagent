from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.lead_extraction import LeadExtractionAgentOutput, LeadExtractionCandidate
from app.schemas.lead_grading import LeadGradingAgentOutput, LeadGradingSuggestion


CONTACT_FIELDS = ("email", "phone")
HARD_RULE_EXPECTATIONS = {
    "forbidden_source": ("Invalid", "risk_blocked"),
    "do_not_contact": ("Invalid", "risk_blocked"),
    "existing_invalid": ("Invalid", "risk_blocked"),
    "high_risk_source": ("Watch", "needs_manual_risk_review"),
    "existing_watch": ("Watch", "needs_manual_risk_review"),
    "c_level_compliance_review": ("C", "needs_compliance_review"),
}


@dataclass(frozen=True)
class InvalidContact:
    field_name: str
    value: str
    reason: str = "contact_not_found_in_source_content"

    def as_dict(self) -> dict[str, str]:
        return {"field_name": self.field_name, "value": self.value, "reason": self.reason}


class LeadExtractionGradingValidator:
    def validate(
        self,
        *,
        extraction: LeadExtractionAgentOutput,
        grading: LeadGradingAgentOutput,
        source_content: str,
        risk_flags: list[str],
        expected_contacts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        candidate = extraction.candidates[0] if extraction.candidates else None
        suggestion = grading.suggestions[0] if grading.suggestions else None
        validation_errors: list[str] = []

        schema_passed = candidate is not None and suggestion is not None and not extraction.validation_errors
        if not schema_passed:
            validation_errors.append("schema 校验失败")

        evidence_hit_rate = self.evidence_hit_rate(candidate)
        invalid_contacts = self.invalid_contacts(
            candidate=candidate,
            source_content=source_content,
            expected_contacts=expected_contacts or {},
        )
        contact_passed = not invalid_contacts
        if not contact_passed:
            validation_errors.append("联系方式反编造校验失败")

        hard_rule_consistency_rate = self.hard_rule_consistency_rate(
            suggestion=suggestion,
            risk_flags=risk_flags,
        )
        if hard_rule_consistency_rate < 1:
            validation_errors.append("硬规则一致率低于 100%")

        return {
            "schema_passed": schema_passed,
            "schema_pass_rate": 1.0 if schema_passed else 0.0,
            "evidence_hit_rate": evidence_hit_rate,
            "contact_anti_fabrication_passed": contact_passed,
            "contact_anti_fabrication_pass_rate": 1.0 if contact_passed else 0.0,
            "hard_rule_consistency_rate": hard_rule_consistency_rate,
            "invalid_contacts": [item.as_dict() for item in invalid_contacts],
            "validation_errors": validation_errors,
        }

    def evidence_hit_rate(self, candidate: LeadExtractionCandidate | None) -> float:
        if candidate is None:
            return 0.0
        fields = [
            candidate.company_name,
            candidate.email,
            candidate.phone,
            candidate.country,
            candidate.city,
            candidate.vehicle_interest,
            candidate.export_intent,
            candidate.website,
        ]
        evidence_hits = sum(1 for field in fields if field.value is not None and field.evidence is not None)
        return round(evidence_hits / len(fields), 4)

    def invalid_contacts(
        self,
        *,
        candidate: LeadExtractionCandidate | None,
        source_content: str,
        expected_contacts: dict[str, Any],
    ) -> list[InvalidContact]:
        if candidate is None:
            return []
        normalized_source = self.normalize(source_content)
        values: dict[str, str | None] = {
            "email": candidate.email.value,
            "phone": candidate.phone.value,
        }
        for field_name in CONTACT_FIELDS:
            expected_value = expected_contacts.get(field_name)
            if expected_value:
                values[field_name] = str(expected_value)

        invalid: list[InvalidContact] = []
        for field_name, value in values.items():
            if not value:
                continue
            if self.normalize(value) not in normalized_source:
                invalid.append(InvalidContact(field_name=field_name, value=value))
        return invalid

    def hard_rule_consistency_rate(
        self,
        *,
        suggestion: LeadGradingSuggestion | None,
        risk_flags: list[str],
    ) -> float:
        if suggestion is None:
            return 0.0
        expected = [HARD_RULE_EXPECTATIONS[flag] for flag in risk_flags if flag in HARD_RULE_EXPECTATIONS]
        if not expected:
            return 1.0
        matched = sum(
            1
            for expected_grade, expected_route in expected
            if suggestion.recommended_grade == expected_grade and suggestion.status_route == expected_route
        )
        return round(matched / len(expected), 4)

    @staticmethod
    def normalize(value: str) -> str:
        return " ".join(value.lower().split())
