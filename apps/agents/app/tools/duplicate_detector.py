from __future__ import annotations

from typing import Any


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _contact_values(lead: dict[str, Any]) -> set[str]:
    contacts = lead.get("contacts_json") or []
    values: set[str] = set()
    if not isinstance(contacts, list):
        return values
    for contact in contacts:
        if not isinstance(contact, dict):
            continue
        value = _normalize_text(contact.get("value"))
        if value:
            values.add(value)
    return values


class DuplicateDetector:
    def find_duplicates(self, leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        for index, current in enumerate(leads):
            current_name = _normalize_text(current.get("customer_name"))
            current_city = _normalize_text(current.get("city"))
            current_contacts = _contact_values(current)
            if not current_name:
                continue

            for previous in leads[:index]:
                previous_name = _normalize_text(previous.get("customer_name"))
                if current_name != previous_name:
                    continue

                previous_contacts = _contact_values(previous)
                matched_contacts = sorted(current_contacts & previous_contacts)
                if matched_contacts:
                    suggestions.append(
                        {
                            "staging_lead_id": current.get("staging_lead_id"),
                            "target_lead_id": previous.get("staging_lead_id"),
                            "suggestion_type": "strong_duplicate",
                            "confidence_score": 0.95,
                            "reason": "客户名称和联系方式一致，建议人工复核后归并。",
                            "evidence_json": {
                                "matched_fields": ["customer_name", "contact"],
                                "matched_contacts": matched_contacts,
                            },
                            "recommended_action": "人工复核重复关系，确认后执行归并",
                        }
                    )
                    break

                previous_city = _normalize_text(previous.get("city"))
                if current_city and current_city == previous_city:
                    suggestions.append(
                        {
                            "staging_lead_id": current.get("staging_lead_id"),
                            "target_lead_id": previous.get("staging_lead_id"),
                            "suggestion_type": "possible_duplicate",
                            "confidence_score": 0.72,
                            "reason": "客户名称和城市一致，建议人工确认是否重复。",
                            "evidence_json": {
                                "matched_fields": ["customer_name", "city"],
                                "matched_city": current_city,
                            },
                            "recommended_action": "人工复核疑似重复关系",
                        }
                    )
                    break
        return suggestions
