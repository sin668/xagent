import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ComplianceReview, ContactMethod, Customer, LeadSource, ReviewLog, StagingLead
from app.models.enums import (
    ChannelRiskLevel,
    ComplianceReviewStatus,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    SourcePlatform,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.schemas.customer_promotion import CustomerPromotionEligibilityResponse, PromoteStagingLeadToCustomerRequest
from app.services.compliance_guards import Phase3ComplianceGuardService
from app.services.staging_leads import StagingLeadService


class CustomerPromotionEligibilityService:
    OPTIONAL_FIELDS = ("customer_type", "scale_signal", "vehicle_intents")

    @staticmethod
    def _has_text(value: object) -> bool:
        text = str(value or "").strip()
        return bool(text) and text.lower() != "unknown"

    @staticmethod
    def _has_contact(contacts_json: list | None) -> bool:
        return any(
            isinstance(item, dict) and str(item.get("value", "")).strip()
            for item in (contacts_json or [])
        )

    @classmethod
    def pending_optional_fields(cls, lead) -> list[str]:
        pending: list[str] = []
        if getattr(lead, "customer_type", None) in {None, CustomerType.UNKNOWN, "unknown"}:
            pending.append("customer_type")
        if not cls._has_text(getattr(lead, "scale_signal", None)):
            pending.append("scale_signal")
        pending.append("vehicle_intents")
        return pending

    @classmethod
    def evaluate(cls, lead, *, has_do_not_contact_match: bool) -> CustomerPromotionEligibilityResponse:
        reasons: list[str] = []
        missing_required_fields: list[str] = []
        candidate = getattr(lead, "candidate_url", None)
        source_url = getattr(candidate, "url", None)
        risk_level = ChannelRiskLevel(getattr(candidate, "source_risk_level", ChannelRiskLevel.LOW))
        grade = CustomerGrade(getattr(lead, "recommended_grade"))
        review_status = StagingReviewStatus(getattr(lead, "review_status"))

        if not cls._has_text(getattr(lead, "customer_name", None)):
            missing_required_fields.append("customer_name")
            reasons.append("缺少客户名称")

        has_country = cls._has_text(getattr(lead, "country", None))
        has_city = cls._has_text(getattr(lead, "city", None))
        if not (has_country and has_city):
            missing_required_fields.append("country_or_city")
            reasons.append("缺少国家/城市")

        if not cls._has_contact(getattr(lead, "contacts_json", None)):
            missing_required_fields.append("contact_method")
            reasons.append("缺少至少一个联系方式")

        if not cls._has_text(source_url):
            missing_required_fields.append("source_url")
            reasons.append("缺少来源链接")

        if not cls._has_text(getattr(lead, "source_evidence", None)):
            missing_required_fields.append("source_evidence")
            reasons.append("缺少来源证据")

        if has_do_not_contact_match:
            reasons.append("命中勿扰客户")

        if risk_level == ChannelRiskLevel.FORBIDDEN:
            reasons.append("Forbidden 来源不得作为客户晋级关键来源")

        if risk_level == ChannelRiskLevel.HIGH and review_status != StagingReviewStatus.APPROVED:
            reasons.append("High 来源未完成二次复核")

        if grade == CustomerGrade.WATCH:
            reasons.append("Watch 不得晋级客户或进入触达队列")
        elif grade == CustomerGrade.INVALID:
            reasons.append("Invalid 不得晋级客户或进入触达队列")

        requires_compliance_review = grade == CustomerGrade.C or bool(getattr(lead, "requires_compliance_review", False))
        blocking_reason_count = len(reasons)
        if grade == CustomerGrade.C:
            reasons.append("C 级客户报价/合同前必须合规复核")

        can_promote = not missing_required_fields and blocking_reason_count == 0
        if can_promote and "满足平衡准入" not in reasons:
            reasons.insert(0, "满足平衡准入")

        return CustomerPromotionEligibilityResponse(
            staging_lead_id=lead.id,
            can_promote=can_promote,
            status="ready" if can_promote else "blocked",
            reasons=reasons,
            missing_required_fields=missing_required_fields,
            pending_optional_fields=cls.pending_optional_fields(lead),
            requires_compliance_review=requires_compliance_review,
            source_url=source_url,
        )


@dataclass
class CustomerPromotionPayloads:
    eligibility: CustomerPromotionEligibilityResponse
    customer: dict
    lead_source: dict
    contact_methods: list[dict]
    compliance_review: dict | None
    review_log: dict


class CustomerPromotionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def core_external_id(lead_id: UUID | str) -> str:
        return f"staging:{lead_id}"

    @staticmethod
    def status_after_promotion(grade: CustomerGrade | str, *, do_not_contact: bool) -> CustomerStatus:
        if do_not_contact:
            return CustomerStatus.DO_NOT_CONTACT
        normalized_grade = CustomerGrade(grade)
        if normalized_grade == CustomerGrade.C:
            return CustomerStatus.READY_FOR_SALES
        return CustomerStatus.READY_FOR_CUSTOMER_SERVICE

    @staticmethod
    def normalize_contact_method_type(value: object) -> ContactMethodType:
        normalized = str(value or "").strip().lower()
        aliases = {
            "email": ContactMethodType.EMAIL,
            "mail": ContactMethodType.EMAIL,
            "phone": ContactMethodType.PHONE,
            "tel": ContactMethodType.PHONE,
            "whatsapp": ContactMethodType.WHATSAPP,
            "telegram": ContactMethodType.TELEGRAM,
            "vk": ContactMethodType.VKONTAKTE,
            "vkontakte": ContactMethodType.VKONTAKTE,
            "ok": ContactMethodType.ODNOKLASSNIKI,
            "odnoklassniki": ContactMethodType.ODNOKLASSNIKI,
            "tiktok": ContactMethodType.TIKTOK,
            "max": ContactMethodType.MAX,
            "website": ContactMethodType.WEBSITE,
            "site": ContactMethodType.WEBSITE,
            "website_form": ContactMethodType.WEBSITE_FORM,
        }
        return aliases.get(normalized, ContactMethodType.OTHER)

    @classmethod
    def build_contact_method_payloads(cls, lead, *, source_url: str, evidence_note: str) -> list[dict]:
        payloads: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for index, contact in enumerate(getattr(lead, "contacts_json", None) or []):
            if not isinstance(contact, dict):
                continue
            value = str(contact.get("value") or "").strip()
            if not value:
                continue
            method_type = cls.normalize_contact_method_type(contact.get("type") or contact.get("method_type"))
            dedupe_key = (method_type.value, value)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            payloads.append(
                {
                    "method_type": method_type,
                    "value": value,
                    "label": contact.get("usage") or contact.get("label"),
                    "source_url": source_url,
                    "evidence_note": evidence_note,
                    "is_primary": index == 0,
                    "dedupe_key": dedupe_key,
                }
            )
        return payloads

    @classmethod
    def build_promotion_payloads(
        cls,
        lead,
        *,
        request: PromoteStagingLeadToCustomerRequest,
        has_do_not_contact_match: bool,
    ) -> CustomerPromotionPayloads:
        eligibility = CustomerPromotionEligibilityService.evaluate(
            lead,
            has_do_not_contact_match=has_do_not_contact_match,
        )
        if not eligibility.can_promote:
            raise ValueError("；".join(eligibility.reasons))

        candidate = getattr(lead, "candidate_url", None)
        source_url = getattr(candidate, "url", "") or ""
        if candidate is not None:
            Phase3ComplianceGuardService.ensure_source_can_be_promotion_key_evidence(
                getattr(candidate, "source_risk_level", ChannelRiskLevel.LOW),
                target_ref=f"staging:{lead.id}",
                actor=request.actor,
            )
        evidence_note = (getattr(lead, "source_evidence", None) or "").strip()
        external_id = cls.core_external_id(lead.id)
        grade = CustomerGrade(getattr(lead, "recommended_grade"))
        do_not_contact = False

        customer_payload = {
            "external_id": external_id,
            "name": lead.customer_name,
            "normalized_name": lead.customer_name.strip().lower(),
            "country": lead.country,
            "city": lead.city,
            "customer_type": CustomerType(getattr(lead, "customer_type", CustomerType.UNKNOWN)),
            "grade": grade,
            "status": cls.status_after_promotion(grade, do_not_contact=do_not_contact),
            "do_not_contact": do_not_contact,
            "ai_recommended_grade": grade,
            "ai_recommendation_reason": getattr(lead, "recommended_reason", None),
            "missing_fields": ", ".join(str(item) for item in (getattr(lead, "missing_fields", None) or [])),
            "owner": request.actor,
            "requires_compliance_review": eligibility.requires_compliance_review,
        }
        lead_source_payload = {
            "external_id": external_id,
            "platform": getattr(candidate, "source_platform", SourcePlatform.OTHER) if candidate is not None else SourcePlatform.OTHER,
            "source_url": source_url,
            "source_title": None,
            "evidence_note": evidence_note,
            "evidence_excerpt": None,
            "channel_risk_level": getattr(candidate, "source_risk_level", ChannelRiskLevel.LOW) if candidate is not None else ChannelRiskLevel.LOW,
            "collected_by": request.actor,
        }
        compliance_payload = (
            {
                "status": ComplianceReviewStatus.PENDING,
                "reason": "C级线索晋级 core 后，报价/合同前必须合规复核。",
                "risk_note": "待复核贸易、支付、物流、清关风险。",
            }
            if eligibility.requires_compliance_review
            else None
        )
        accepted_fields_text = json.dumps(
            request.accepted_fields_json,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        review_log_payload = {
            "task_id": str(lead.id),
            "agent_name": "manual-review",
            "action": "lead_promoted_to_customer",
            "reviewer": request.actor,
            "input_ref": f"staging:{lead.id};accepted_fields_json={accepted_fields_text}",
            "output_ref": f"customer_external_id:{external_id}",
            "result": "approved",
            "error_message": request.review_note,
        }
        return CustomerPromotionPayloads(
            eligibility=eligibility,
            customer=customer_payload,
            lead_source=lead_source_payload,
            contact_methods=cls.build_contact_method_payloads(lead, source_url=source_url, evidence_note=evidence_note),
            compliance_review=compliance_payload,
            review_log=review_log_payload,
        )

    def get_staging_lead(self, lead_id: UUID) -> StagingLead | None:
        return self.session.get(StagingLead, lead_id)

    def find_do_not_contact_customer_id(self, lead: StagingLead) -> UUID | None:
        contact_values = {
            str(item.get("value", "")).strip().lower()
            for item in (lead.contacts_json or [])
            if isinstance(item, dict) and str(item.get("value", "")).strip()
        }
        normalized_name = (lead.customer_name or "").strip().lower()
        if normalized_name and normalized_name != "unknown":
            matched_customer_id = self.session.scalar(
                select(Customer.id)
                .where(
                    Customer.do_not_contact.is_(True),
                    (Customer.normalized_name == normalized_name) | (func.lower(Customer.name) == normalized_name),
                )
                .limit(1)
            )
            if matched_customer_id:
                return matched_customer_id
        if not contact_values:
            return None
        return self.session.scalar(
            select(Customer.id)
            .join(ContactMethod, ContactMethod.customer_id == Customer.id)
            .where(Customer.do_not_contact.is_(True), func.lower(ContactMethod.value).in_(contact_values))
            .limit(1)
        )

    def has_do_not_contact_match(self, lead: StagingLead) -> bool:
        return self.find_do_not_contact_customer_id(lead) is not None

    def promote_to_customer(self, lead: StagingLead, *, request: PromoteStagingLeadToCustomerRequest) -> dict:
        payloads = self.build_promotion_payloads(
            lead,
            request=request,
            has_do_not_contact_match=self.has_do_not_contact_match(lead),
        )
        customer = self.session.scalar(select(Customer).where(Customer.external_id == payloads.customer["external_id"]))
        if customer is None:
            customer = Customer(external_id=payloads.customer["external_id"], name=payloads.customer["name"])
            self.session.add(customer)
        for field in (
            "name",
            "normalized_name",
            "country",
            "city",
            "customer_type",
            "grade",
            "status",
            "do_not_contact",
            "ai_recommended_grade",
            "ai_recommendation_reason",
            "missing_fields",
            "owner",
        ):
            setattr(customer, field, payloads.customer[field])
        self.session.flush()

        lead_source = self.session.scalar(select(LeadSource).where(LeadSource.external_id == payloads.lead_source["external_id"]))
        if lead_source is None:
            lead_source = LeadSource(external_id=payloads.lead_source["external_id"], customer_id=customer.id)
            self.session.add(lead_source)
        lead_source.customer_id = customer.id
        for field in (
            "platform",
            "source_url",
            "source_title",
            "evidence_note",
            "evidence_excerpt",
            "channel_risk_level",
            "collected_by",
        ):
            setattr(lead_source, field, payloads.lead_source[field])

        contact_methods: list[ContactMethod] = []
        for contact_payload in payloads.contact_methods:
            existing = self.session.scalar(
                select(ContactMethod).where(
                    ContactMethod.customer_id == customer.id,
                    ContactMethod.method_type == contact_payload["method_type"],
                    ContactMethod.value == contact_payload["value"],
                )
            )
            if existing is None:
                existing = ContactMethod(customer_id=customer.id)
                self.session.add(existing)
            for field in ("method_type", "value", "label", "source_url", "evidence_note", "is_primary"):
                setattr(existing, field, contact_payload[field])
            contact_methods.append(existing)

        compliance_review = None
        if payloads.compliance_review is not None:
            compliance_review = self.session.scalar(
                select(ComplianceReview)
                .where(ComplianceReview.customer_id == customer.id)
                .order_by(ComplianceReview.created_at.desc(), ComplianceReview.id.desc())
            )
            if compliance_review is None:
                compliance_review = ComplianceReview(customer_id=customer.id)
                self.session.add(compliance_review)
            compliance_review.status = payloads.compliance_review["status"]
            compliance_review.reason = payloads.compliance_review["reason"]
            compliance_review.risk_note = payloads.compliance_review["risk_note"]

        lead.review_status = StagingReviewStatus.APPROVED
        lead.queue_status = StagingQueueStatus.ELIGIBLE
        review_log = ReviewLog(**payloads.review_log)
        self.session.add(review_log)
        self.session.flush()
        return {
            "lead": lead,
            "customer": customer,
            "lead_source": lead_source,
            "contact_methods": contact_methods,
            "compliance_review": compliance_review,
            "review_log": review_log,
            "requires_compliance_review": payloads.eligibility.requires_compliance_review,
        }
