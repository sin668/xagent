from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Customer
from app.models.enums import (
    ComplianceReviewStatus,
    CustomerGrade,
    CustomerStatus,
    OutreachStatus,
)
from app.schemas.customer import CustomerDetailResponse
from app.services.customer_status import CustomerAssignmentStatusService


@dataclass(slots=True)
class CustomerWorkbenchFilters:
    status: CustomerStatus | None = None
    grade: CustomerGrade | None = None
    owner: str | None = None
    country: str | None = None
    city: str | None = None
    limit: int = 100


@dataclass(slots=True)
class CustomerWorkbenchItem:
    customer: Customer
    contact_summary: dict
    source_completeness: dict
    completeness_score: int
    followup_status: str
    vehicle_intent_summary: dict
    next_action: str
    next_action_priority: int

    def __getattr__(self, name):
        return getattr(self.customer, name)


class CustomersWorkbenchService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _today_bounds(now: datetime) -> tuple[datetime, datetime]:
        normalized = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
        start = normalized.replace(hour=0, minute=0, second=0, microsecond=0)
        end = normalized.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    @staticmethod
    def build_workbench_query(filters: CustomerWorkbenchFilters):
        query = (
            select(Customer)
            .options(
                selectinload(Customer.contact_methods),
                selectinload(Customer.sources),
                selectinload(Customer.vehicle_intents),
                selectinload(Customer.outreach_records),
                selectinload(Customer.followups),
                selectinload(Customer.compliance_reviews),
            )
            .where(Customer.do_not_contact.is_(False))
            .where(Customer.grade.notin_([CustomerGrade.WATCH, CustomerGrade.INVALID]))
            .where(Customer.status.notin_([CustomerStatus.WATCH, CustomerStatus.INVALID, CustomerStatus.DO_NOT_CONTACT]))
        )
        if filters.status is not None:
            query = query.where(Customer.status == filters.status)
        if filters.grade is not None:
            query = query.where(Customer.grade == filters.grade)
        if filters.owner:
            query = query.where(Customer.owner == filters.owner)
        if filters.country:
            query = query.where(Customer.country == filters.country)
        if filters.city:
            query = query.where(Customer.city == filters.city)
        return query.order_by(Customer.updated_at.desc(), Customer.name.asc()).limit(filters.limit)

    def list_workbench_customers(
        self,
        filters: CustomerWorkbenchFilters,
        *,
        now: datetime | None = None,
    ) -> list[CustomerWorkbenchItem]:
        timestamp = now or datetime.now(UTC)
        rows = list(self.session.scalars(self.build_workbench_query(filters)).all())
        visible = CustomerAssignmentStatusService.filter_workbench_customers(rows)
        items = [self.build_item(customer, now=timestamp) for customer in visible]
        return sorted(items, key=lambda item: (item.next_action_priority, self._updated_at_sort_value(item.customer), item.customer.name))

    def get_customer_detail(self, customer_id: UUID, *, now: datetime | None = None) -> CustomerDetailResponse:
        customer = self.session.scalar(self.build_detail_query(customer_id))
        if customer is None:
            raise ValueError(f"客户不存在: {customer_id}")
        timestamp = now or datetime.now(UTC)
        item = self.build_item(customer, now=timestamp)
        next_action = "勿扰客户，不得触达" if bool(customer.do_not_contact) else item.next_action
        next_action_priority = 99 if bool(customer.do_not_contact) else item.next_action_priority
        return CustomerDetailResponse(
            id=str(customer.id),
            profile=self.profile(customer),
            contacts=self.serialize_contacts(customer),
            sources=self.serialize_sources(customer),
            vehicle_intents=self.serialize_vehicle_intents(customer),
            outreach_history=self.serialize_outreach_history(customer),
            followups=self.serialize_followups(customer),
            compliance_status=self.compliance_status(customer),
            do_not_contact=self.do_not_contact_status(customer),
            pending_fields=self.pending_fields(customer),
            source_traceability=self.source_traceability(customer),
            contact_summary=item.contact_summary,
            source_completeness=item.source_completeness,
            completeness_score=item.completeness_score,
            vehicle_intent_summary=item.vehicle_intent_summary,
            followup_status=item.followup_status,
            next_action=next_action,
            next_action_priority=next_action_priority,
        )

    @staticmethod
    def build_detail_query(customer_id: UUID):
        return (
            select(Customer)
            .options(
                selectinload(Customer.contact_methods),
                selectinload(Customer.sources),
                selectinload(Customer.vehicle_intents),
                selectinload(Customer.outreach_records),
                selectinload(Customer.followups),
                selectinload(Customer.compliance_reviews),
            )
            .where(Customer.id == customer_id)
        )

    @staticmethod
    def _updated_at_sort_value(customer: Customer) -> float:
        updated_at = getattr(customer, "updated_at", None)
        if updated_at is None:
            return 0
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return -updated_at.timestamp()

    @classmethod
    def build_item(cls, customer: Customer, *, now: datetime | None = None) -> CustomerWorkbenchItem:
        timestamp = now or datetime.now(UTC)
        contact_summary = cls.contact_summary(customer)
        source_completeness = cls.source_completeness(customer)
        vehicle_intent_summary = cls.vehicle_intent_summary(customer)
        next_action, priority = cls.next_action(customer, now=timestamp)
        return CustomerWorkbenchItem(
            customer=customer,
            contact_summary=contact_summary,
            source_completeness=source_completeness,
            completeness_score=cls.completeness_score(customer, contact_summary, source_completeness, vehicle_intent_summary),
            followup_status=cls.followup_status(customer, now=timestamp),
            vehicle_intent_summary=vehicle_intent_summary,
            next_action=next_action,
            next_action_priority=priority,
        )

    @staticmethod
    def contact_summary(customer: Customer) -> dict:
        contacts = list(getattr(customer, "contact_methods", None) or [])
        primary = next((item for item in contacts if bool(getattr(item, "is_primary", False))), contacts[0] if contacts else None)
        types = sorted({item.method_type.value for item in contacts})
        return {
            "total": len(contacts),
            "types": types,
            "primary": f"{primary.method_type.value}:{primary.value}" if primary is not None else None,
            "has_email": any(item.method_type.value == "email" for item in contacts),
            "has_social": any(item.method_type.value in {"whatsapp", "telegram", "vkontakte", "odnoklassniki", "tiktok", "max"} for item in contacts),
        }

    @staticmethod
    def pending_fields(customer: Customer) -> list[str]:
        raw = str(getattr(customer, "missing_fields", "") or "").strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    @staticmethod
    def profile(customer: Customer) -> dict:
        return {
            "id": str(customer.id),
            "external_id": customer.external_id,
            "name": customer.name,
            "country": customer.country,
            "city": customer.city,
            "customer_type": customer.customer_type.value,
            "grade": customer.grade.value,
            "status": customer.status.value,
            "owner": customer.owner,
            "owner_team": getattr(customer, "owner_team", None),
            "ai_recommended_grade": customer.ai_recommended_grade.value if customer.ai_recommended_grade else None,
            "ai_recommendation_reason": customer.ai_recommendation_reason,
            "created_at": customer.created_at.isoformat() if getattr(customer, "created_at", None) else None,
            "updated_at": customer.updated_at.isoformat() if getattr(customer, "updated_at", None) else None,
        }

    @staticmethod
    def serialize_contacts(customer: Customer) -> list[dict]:
        return [
            {
                "id": str(item.id),
                "type": item.method_type.value,
                "value": item.value,
                "label": item.label,
                "source_url": item.source_url,
                "evidence_note": item.evidence_note,
                "is_primary": item.is_primary,
                "is_verified": item.is_verified,
            }
            for item in getattr(customer, "contact_methods", None) or []
        ]

    @staticmethod
    def serialize_sources(customer: Customer) -> list[dict]:
        return [
            {
                "id": str(item.id),
                "platform": item.platform.value,
                "source_url": item.source_url,
                "source_title": item.source_title,
                "evidence_note": item.evidence_note,
                "evidence_excerpt": item.evidence_excerpt,
                "risk_level": item.channel_risk_level.value,
                "collected_by": item.collected_by,
                "collected_at": item.collected_at.isoformat() if getattr(item, "collected_at", None) else None,
            }
            for item in getattr(customer, "sources", None) or []
        ]

    @staticmethod
    def source_completeness(customer: Customer) -> dict:
        sources = list(getattr(customer, "sources", None) or [])
        has_evidence = any(bool(str(getattr(item, "evidence_note", "") or "").strip()) for item in sources)
        risk_levels = sorted({item.channel_risk_level.value for item in sources})
        return {
            "source_count": len(sources),
            "has_source_url": any(bool(str(getattr(item, "source_url", "") or "").strip()) for item in sources),
            "has_evidence": has_evidence,
            "risk_levels": risk_levels,
        }

    @staticmethod
    def vehicle_intent_summary(customer: Customer) -> dict:
        intents = list(getattr(customer, "vehicle_intents", None) or [])
        active = [item for item in intents if str(getattr(item, "status", "")) in {"active", "pending_confirmation"}]
        items = [
            {
                "id": str(item.id),
                "brand": item.brand,
                "model": item.model,
                "quantity": item.quantity,
                "budget_range": item.budget_range,
                "label": " ".join(part for part in [item.brand, item.model] if part) or "待确认车型",
            }
            for item in active[:3]
        ]
        return {"total": len(active), "items": items}

    @staticmethod
    def serialize_vehicle_intents(customer: Customer) -> list[dict]:
        return [
            {
                "id": str(item.id),
                "brand": item.brand,
                "model": item.model,
                "year_range": item.year_range,
                "vehicle_age": item.vehicle_age,
                "quantity": item.quantity,
                "budget_range": item.budget_range,
                "purchase_frequency": item.purchase_frequency,
                "delivery_country": item.delivery_country,
                "delivery_city": item.delivery_city,
                "concerns": item.concerns or [],
                "source_type": item.source_type.value,
                "source_note": item.source_note,
                "status": item.status.value,
                "created_by": item.created_by,
                "label": " ".join(part for part in [item.brand, item.model] if part) or "待确认车型",
                "created_at": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
            }
            for item in getattr(customer, "vehicle_intents", None) or []
        ]

    @staticmethod
    def serialize_outreach_history(customer: Customer) -> list[dict]:
        records = sorted(
            getattr(customer, "outreach_records", None) or [],
            key=lambda item: getattr(item, "created_at", datetime.min),
            reverse=True,
        )
        return [
            {
                "id": str(item.id),
                "channel": item.channel.value,
                "status": item.status.value,
                "sent_by": item.sent_by,
                "owner": item.owner,
                "sent_at": item.sent_at.isoformat() if getattr(item, "sent_at", None) else None,
                "response_summary": item.response_summary,
                "next_action": item.next_action,
                "triggers_do_not_contact": item.triggers_do_not_contact,
                "created_at": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
            }
            for item in records
        ]

    @staticmethod
    def serialize_followups(customer: Customer) -> list[dict]:
        records = sorted(
            getattr(customer, "followups", None) or [],
            key=lambda item: getattr(item, "created_at", datetime.min),
            reverse=True,
        )
        return [
            {
                "id": str(item.id),
                "owner_id": item.owner_id,
                "team": item.team.value,
                "followup_type": item.followup_type.value,
                "content": item.content,
                "customer_feedback": item.customer_feedback,
                "next_action": item.next_action,
                "next_followup_at": item.next_followup_at.isoformat() if getattr(item, "next_followup_at", None) else None,
                "triggered_dnc": item.triggered_dnc,
                "triggered_compliance_review": item.triggered_compliance_review,
                "created_by": item.created_by,
                "created_at": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
            }
            for item in records
        ]

    @staticmethod
    def do_not_contact_status(customer: Customer) -> dict:
        return {
            "enabled": bool(customer.do_not_contact),
            "reason": customer.do_not_contact_reason,
            "marked_by": customer.do_not_contact_marked_by,
            "marked_at": customer.do_not_contact_marked_at.isoformat()
            if getattr(customer, "do_not_contact_marked_at", None)
            else None,
        }

    @staticmethod
    def compliance_status(customer: Customer) -> dict:
        reviews = sorted(
            getattr(customer, "compliance_reviews", None) or [],
            key=lambda item: getattr(item, "created_at", datetime.min),
            reverse=True,
        )
        latest = reviews[0] if reviews else None
        return {
            "requires_review": CustomerGrade(customer.grade) == CustomerGrade.C or latest is not None,
            "latest_status": latest.status.value if latest is not None else None,
            "latest_reason": latest.reason if latest is not None else None,
            "latest_risk_note": latest.risk_note if latest is not None else None,
            "reviewer": latest.reviewer if latest is not None else None,
            "reviewed_at": latest.reviewed_at.isoformat() if latest is not None and latest.reviewed_at else None,
        }

    @staticmethod
    def source_traceability(customer: Customer) -> dict:
        sources = list(getattr(customer, "sources", None) or [])
        contacts = list(getattr(customer, "contact_methods", None) or [])
        source_urls = sorted(
            {
                str(value).strip()
                for value in [
                    *[getattr(item, "source_url", None) for item in sources],
                    *[getattr(item, "source_url", None) for item in contacts],
                ]
                if str(value or "").strip()
            }
        )
        return {
            "lead_sources_count": len(sources),
            "contact_evidence_count": sum(
                1 for item in contacts if str(getattr(item, "evidence_note", "") or "").strip()
            ),
            "source_urls": source_urls,
            "has_enrichment_evidence": bool(sources)
            or any(str(getattr(item, "evidence_note", "") or "").strip() for item in contacts),
        }

    @staticmethod
    def latest_outreach(customer: Customer):
        records = list(getattr(customer, "outreach_records", None) or [])
        return max(records, key=lambda item: getattr(item, "created_at", datetime.min), default=None)

    @staticmethod
    def latest_followup(customer: Customer):
        records = list(getattr(customer, "followups", None) or [])
        return max(records, key=lambda item: getattr(item, "created_at", datetime.min), default=None)

    @classmethod
    def has_today_followup(cls, customer: Customer, *, now: datetime) -> bool:
        start, end = cls._today_bounds(now)
        for item in getattr(customer, "followups", None) or []:
            next_at = getattr(item, "next_followup_at", None)
            if next_at is None:
                continue
            if next_at.tzinfo is None:
                next_at = next_at.replace(tzinfo=UTC)
            if start <= next_at <= end:
                return True
        return False

    @staticmethod
    def has_pending_compliance(customer: Customer) -> bool:
        return any(
            ComplianceReviewStatus(getattr(item, "status")) == ComplianceReviewStatus.PENDING
            for item in getattr(customer, "compliance_reviews", None) or []
        )

    @classmethod
    def followup_status(cls, customer: Customer, *, now: datetime) -> str:
        if cls.has_today_followup(customer, now=now):
            return "today_due"
        latest = cls.latest_outreach(customer)
        if latest is None:
            return "not_contacted"
        if OutreachStatus(latest.status) == OutreachStatus.REPLIED:
            return "replied"
        return OutreachStatus(latest.status).value

    @classmethod
    def next_action(cls, customer: Customer, *, now: datetime) -> tuple[str, int]:
        if cls.has_today_followup(customer, now=now):
            return "今日待跟进", 1
        if CustomerGrade(customer.grade) == CustomerGrade.C and cls.has_pending_compliance(customer):
            return "C级待合规复核", 2
        latest_outreach = cls.latest_outreach(customer)
        if latest_outreach is not None and OutreachStatus(latest_outreach.status) == OutreachStatus.REPLIED:
            return "已回复待销售承接", 3
        if cls.has_missing_customer_info(customer):
            return "待补全客户信息", 5
        if latest_outreach is None and CustomerStatus(customer.status) in {
            CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
            CustomerStatus.READY_FOR_SALES,
            CustomerStatus.PENDING_REVIEW,
            CustomerStatus.NEW,
        }:
            return "待首次触达", 4
        if CustomerStatus(customer.status) in {CustomerStatus.SALES_FOLLOWING, CustomerStatus.READY_FOR_SALES}:
            return "销售跟进中", 6
        return "暂停/低优先级", 7

    @staticmethod
    def has_missing_customer_info(customer: Customer) -> bool:
        missing_fields = str(getattr(customer, "missing_fields", "") or "").strip()
        if missing_fields:
            return True
        if not list(getattr(customer, "vehicle_intents", None) or []):
            return True
        return False

    @staticmethod
    def completeness_score(customer: Customer, contact_summary: dict, source_completeness: dict, vehicle_intent_summary: dict) -> int:
        score = 0
        if str(getattr(customer, "name", "") or "").strip() and str(getattr(customer, "country", "") or "").strip():
            score += 20
        if contact_summary.get("total", 0) > 0:
            score += 25
        if source_completeness.get("has_source_url") and source_completeness.get("has_evidence"):
            score += 25
        if not CustomersWorkbenchService.has_missing_customer_info(customer):
            score += 15
        if vehicle_intent_summary.get("total", 0) > 0:
            score += 15
        return min(score, 100)
