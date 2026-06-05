from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.customer import Customer
from app.models.email_message import EmailMessage


class EmailReplyContextBuilder:
    SENSITIVE_DATA_POLICY = "只包含邮件回复所需客户、来信、触达、意向、来源风险和知识命中摘要。"
    INCLUDED_SECTIONS = [
        "customer",
        "inbound_message",
        "recent_outreach_history",
        "vehicle_intents",
        "source_risk",
        "knowledge_hits",
        "risk_decision",
    ]
    RISK_ORDER = {"Unknown": 0, "Low": 1, "Medium": 2, "High": 3, "Forbidden": 4}

    @classmethod
    def build(
        cls,
        *,
        customer: Customer | None,
        message: EmailMessage,
        knowledge_hits: list[dict] | None,
        risk_decision: dict | None,
        outreach_limit: int = 5,
    ) -> dict[str, Any]:
        resolved_customer = customer or getattr(message, "customer", None)
        recent_outreach = cls.recent_outreach_history(resolved_customer, limit=outreach_limit)
        vehicle_intents = cls.vehicle_intents(resolved_customer)
        source_risk = cls.source_risk(resolved_customer)
        normalized_knowledge_hits = list(knowledge_hits or [])
        normalized_risk_decision = dict(risk_decision or {})

        return {
            "customer": cls.customer_summary(resolved_customer),
            "inbound_message": cls.inbound_message(message),
            "recent_outreach_history": recent_outreach,
            "vehicle_intents": vehicle_intents,
            "source_risk": source_risk,
            "knowledge_hits": normalized_knowledge_hits,
            "risk_decision": normalized_risk_decision,
            "audit_summary": {
                "included_sections": cls.INCLUDED_SECTIONS,
                "recent_outreach_count": len(recent_outreach),
                "vehicle_intent_count": len(vehicle_intents),
                "knowledge_hit_count": len(normalized_knowledge_hits),
                "source_count": len(source_risk["sources"]),
                "has_risk_decision": bool(normalized_risk_decision),
                "sensitive_data_policy": cls.SENSITIVE_DATA_POLICY,
            },
        }

    @classmethod
    def customer_summary(cls, customer: Customer | None) -> dict[str, Any]:
        if customer is None:
            return {
                "id": None,
                "name": "Unknown",
                "country": "Unknown",
                "city": "Unknown",
                "customer_type": "Unknown",
                "grade": "Unknown",
                "status": "Unknown",
                "owner": "Unknown",
                "owner_team": "Unknown",
                "do_not_contact": {"enabled": False, "reason": None},
            }
        return {
            "id": cls._string_or_none(getattr(customer, "id", None)),
            "name": cls._unknown(getattr(customer, "name", None)),
            "country": cls._unknown(getattr(customer, "country", None)),
            "city": cls._unknown(getattr(customer, "city", None)),
            "customer_type": cls._enum_or_unknown(getattr(customer, "customer_type", None)),
            "grade": cls._enum_or_unknown(getattr(customer, "grade", None)),
            "status": cls._enum_or_unknown(getattr(customer, "status", None)),
            "owner": cls._unknown(getattr(customer, "owner", None)),
            "owner_team": cls._unknown(getattr(customer, "owner_team", None)),
            "do_not_contact": {
                "enabled": bool(getattr(customer, "do_not_contact", False)),
                "reason": getattr(customer, "do_not_contact_reason", None),
            },
        }

    @classmethod
    def inbound_message(cls, message: EmailMessage) -> dict[str, Any]:
        thread = getattr(message, "thread", None)
        return {
            "id": cls._string_or_none(getattr(message, "id", None)),
            "thread_id": cls._string_or_none(getattr(message, "thread_id", None)),
            "thread_subject": cls._unknown(getattr(thread, "subject", None)),
            "thread_status": cls._enum_or_unknown(getattr(thread, "status", None)),
            "direction": cls._enum_or_unknown(getattr(message, "direction", None)),
            "from_email": cls._unknown(getattr(message, "from_email", None)),
            "to_emails": list(getattr(message, "to_emails", None) or []),
            "subject": cls._unknown(getattr(message, "subject", None)),
            "body_text": getattr(message, "body_text", None) or "",
            "language": cls._unknown(getattr(message, "language", None)),
            "status": cls._enum_or_unknown(getattr(message, "status", None)),
            "source_type": cls._enum_or_unknown(getattr(message, "source_type", None)),
            "created_at": cls._iso_or_none(getattr(message, "created_at", None)),
        }

    @classmethod
    def recent_outreach_history(cls, customer: Customer | None, *, limit: int) -> list[dict[str, Any]]:
        records = list(getattr(customer, "outreach_records", None) or [])
        records.sort(key=lambda item: cls._datetime_sort_value(getattr(item, "sent_at", None), getattr(item, "created_at", None)), reverse=True)
        return [
            {
                "id": cls._string_or_none(getattr(record, "id", None)),
                "channel": cls._enum_or_unknown(getattr(record, "channel", None)),
                "status": cls._enum_or_unknown(getattr(record, "status", None)),
                "sent_by": cls._unknown(getattr(record, "sent_by", None)),
                "owner": cls._unknown(getattr(record, "owner", None)),
                "sent_at": cls._iso_or_none(getattr(record, "sent_at", None)),
                "response_summary": cls._unknown(getattr(record, "response_summary", None)),
                "next_action": cls._unknown(getattr(record, "next_action", None)),
                "triggers_do_not_contact": bool(getattr(record, "triggers_do_not_contact", False)),
            }
            for record in records[:limit]
        ]

    @classmethod
    def vehicle_intents(cls, customer: Customer | None) -> list[dict[str, Any]]:
        intents = list(getattr(customer, "vehicle_intents", None) or [])
        return [
            {
                "id": cls._string_or_none(getattr(intent, "id", None)),
                "brand": cls._unknown(getattr(intent, "brand", None)),
                "model": cls._unknown(getattr(intent, "model", None)),
                "year_range": cls._unknown(getattr(intent, "year_range", None)),
                "quantity": getattr(intent, "quantity", None),
                "budget_range": cls._unknown(getattr(intent, "budget_range", None)),
                "delivery_country": cls._unknown(getattr(intent, "delivery_country", None)),
                "delivery_city": cls._unknown(getattr(intent, "delivery_city", None)),
                "concerns": list(getattr(intent, "concerns", None) or []),
                "source_type": cls._enum_or_unknown(getattr(intent, "source_type", None)),
                "source_note": cls._unknown(getattr(intent, "source_note", None)),
                "status": cls._enum_or_unknown(getattr(intent, "status", None)),
            }
            for intent in intents
        ]

    @classmethod
    def source_risk(cls, customer: Customer | None) -> dict[str, Any]:
        sources = []
        highest = "Unknown"
        for source in list(getattr(customer, "sources", None) or []):
            risk = cls._enum_or_unknown(getattr(source, "channel_risk_level", None))
            if cls.RISK_ORDER.get(risk, 0) > cls.RISK_ORDER.get(highest, 0):
                highest = risk
            sources.append(
                {
                    "id": cls._string_or_none(getattr(source, "id", None)),
                    "platform": cls._enum_or_unknown(getattr(source, "platform", None)),
                    "source_url": cls._unknown(getattr(source, "source_url", None)),
                    "source_title": cls._unknown(getattr(source, "source_title", None)),
                    "evidence_note": cls._unknown(getattr(source, "evidence_note", None)),
                    "risk_level": risk,
                    "collected_by": cls._unknown(getattr(source, "collected_by", None)),
                }
            )
        return {"highest_risk_level": highest, "sources": sources}

    @staticmethod
    def _enum_or_unknown(value: Any) -> str:
        raw = value.value if hasattr(value, "value") else value
        return EmailReplyContextBuilder._unknown(raw)

    @staticmethod
    def _unknown(value: Any) -> str:
        text = str(value).strip() if value is not None else ""
        return text or "Unknown"

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _iso_or_none(value: Any) -> str | None:
        return value.isoformat() if hasattr(value, "isoformat") else None

    @staticmethod
    def _datetime_sort_value(*values: Any) -> float:
        for value in values:
            if isinstance(value, datetime):
                return value.timestamp()
        return 0.0
