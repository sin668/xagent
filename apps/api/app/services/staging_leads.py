from __future__ import annotations

import hashlib
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, selectinload

from app.models import AIAuditLog, CandidateUrl, ComplianceReview, ContactMethod, Customer, LeadSource, PageSnapshot, ReviewLog, StagingLead
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
from app.services.compliance_guards import Phase3ComplianceGuardService


class StagingLeadService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def validate_candidate_url_id(candidate_url_id: UUID | str | None) -> None:
        if candidate_url_id is None or str(candidate_url_id).strip() == "":
            raise ValueError("staging lead 必须关联 candidate_url_id。")

    @staticmethod
    def normalize_payload(
        *,
        customer_name: str | None,
        country: str | None,
        city: str | None,
        contacts_json: list | None,
        missing_fields: list | None,
    ) -> dict:
        return {
            "customer_name": (customer_name or "Unknown").strip() or "Unknown",
            "country": (country or "Unknown").strip() or "Unknown",
            "city": city.strip() if isinstance(city, str) and city.strip() else None,
            "contacts_json": contacts_json or [],
            "missing_fields": missing_fields or [],
        }

    @staticmethod
    def default_queue_status(grade: CustomerGrade | str) -> StagingQueueStatus:
        normalized_grade = CustomerGrade(grade)
        if normalized_grade in {CustomerGrade.INVALID, CustomerGrade.WATCH}:
            return StagingQueueStatus.NOT_ELIGIBLE
        return StagingQueueStatus.PENDING_REVIEW

    @staticmethod
    def default_review_status(source_risk_level: ChannelRiskLevel | str) -> StagingReviewStatus:
        risk = ChannelRiskLevel(source_risk_level)
        if risk == ChannelRiskLevel.HIGH:
            return StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION
        return StagingReviewStatus.PENDING_REVIEW

    @staticmethod
    def default_requires_compliance_review(grade: CustomerGrade | str) -> bool:
        return CustomerGrade(grade) == CustomerGrade.C

    @staticmethod
    def build_dedupe_key(customer_name: str, city: str | None, contacts_json: list) -> str:
        contact_values = sorted(str(item.get("value", "")).strip().lower() for item in contacts_json if isinstance(item, dict))
        contact_part = "|".join(value for value in contact_values if value)
        return f"{customer_name.strip().lower()}::{(city or '').strip().lower()}::{contact_part}"

    @staticmethod
    def normalize_customer_name(value: str | None) -> str:
        return " ".join((value or "Unknown").strip().lower().split())

    @staticmethod
    def normalize_contact_value(value: object) -> str:
        return str(value or "").strip().lower()

    @classmethod
    def contact_hash(cls, contacts_json: list | None) -> str:
        values = sorted(
            cls.normalize_contact_value(item.get("value"))
            for item in (contacts_json or [])
            if isinstance(item, dict) and cls.normalize_contact_value(item.get("value"))
        )
        if not values:
            return ""
        return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def source_domain(source_url: str | None) -> str:
        if not source_url:
            return ""
        parsed = urlsplit(source_url)
        host = (parsed.netloc or parsed.path).split("/")[0].lower()
        return host[4:] if host.startswith("www.") else host

    @classmethod
    def source_url_hash(cls, source_url: str | None, fallback_hash: str | None = None) -> str:
        if fallback_hash:
            return fallback_hash
        if not source_url:
            return ""
        normalized = source_url.strip().lower().rstrip("/")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def build_duplicate_keys(cls, lead: StagingLead) -> dict:
        source_url = lead.candidate_url.url if getattr(lead, "candidate_url", None) is not None else None
        url_hash = getattr(getattr(lead, "candidate_url", None), "url_hash", None)
        normalized_name = cls.normalize_customer_name(lead.customer_name)
        contact_hash = cls.contact_hash(lead.contacts_json)
        city = (lead.city or "").strip().lower()
        domain = cls.source_domain(source_url)
        return {
            "normalized_name": normalized_name,
            "contact_hash": contact_hash,
            "strong_key": f"{normalized_name}::{contact_hash}" if contact_hash else "",
            "suspected_key": f"{normalized_name}::{city}::{domain}" if city and domain else "",
            "source_domain": domain,
            "source_url_hash": cls.source_url_hash(source_url, url_hash),
        }

    @staticmethod
    def build_duplicate_signal_summary(
        *,
        strong_candidates: list[dict],
        suspected_candidates: list[dict],
        source_candidates: list[dict],
    ) -> dict:
        return {
            "has_strong_duplicate": bool(strong_candidates),
            "blocks_promotion": bool(strong_candidates),
            "requires_manual_review": bool(strong_candidates or suspected_candidates or source_candidates),
            "strong_duplicates": strong_candidates,
            "suspected_duplicates": suspected_candidates,
            "source_duplicates": source_candidates,
        }

    @classmethod
    def empty_duplicate_signal_summary(cls) -> dict:
        return cls.build_duplicate_signal_summary(
            strong_candidates=[],
            suspected_candidates=[],
            source_candidates=[],
        )

    @staticmethod
    def raise_if_strong_duplicate(signals: dict) -> None:
        if not signals.get("blocks_promotion"):
            return
        reasons = [
            str(candidate.get("reason"))
            for candidate in signals.get("strong_duplicates", [])
            if candidate.get("reason")
        ]
        raise ValueError(f"强重复线索不得晋级 core：{'；'.join(reasons) or '存在强重复'}")

    @staticmethod
    def build_merge_resolution_payload(
        lead: StagingLead,
        *,
        target_customer_id: UUID,
        actor: str,
        source_url: str,
        evidence_note: str,
    ) -> dict:
        return {
            "review_status": StagingReviewStatus.DUPLICATE.value,
            "queue_status": StagingQueueStatus.NOT_ELIGIBLE.value,
            "lead_source": {
                "customer_id": target_customer_id,
                "source_url": source_url,
                "evidence_note": evidence_note,
            },
            "review_log": {
                "task_id": str(lead.id),
                "action": "merge_duplicate_staging_lead",
                "reviewer": actor,
                "input_ref": f"staging:{lead.id}",
                "output_ref": f"customer:{target_customer_id}",
                "result": "merged",
            },
        }

    @staticmethod
    def has_contact(contacts_json: list | None) -> bool:
        return any(
            isinstance(item, dict) and str(item.get("value", "")).strip()
            for item in (contacts_json or [])
        )

    @staticmethod
    def has_valid_customer_name(customer_name: str | None) -> bool:
        normalized = (customer_name or "").strip()
        return bool(normalized) and normalized.lower() != "unknown"

    @staticmethod
    def evidence_status(source_evidence: str | None) -> str:
        return "present" if (source_evidence or "").strip() else "missing"

    @staticmethod
    def risk_markers(
        *,
        source_risk_level: str | ChannelRiskLevel,
        recommended_grade: str | CustomerGrade,
        review_status: str | StagingReviewStatus,
        has_contact: bool,
        has_evidence: bool,
    ) -> list[str]:
        markers: list[str] = []
        risk = ChannelRiskLevel(source_risk_level)
        grade = CustomerGrade(recommended_grade)
        review = StagingReviewStatus(review_status)
        if risk == ChannelRiskLevel.HIGH or review == StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION:
            markers.append("High 二次复核")
        if grade == CustomerGrade.WATCH:
            markers.append("Watch 不进入触达")
        if grade == CustomerGrade.INVALID:
            markers.append("Invalid 不进入触达")
        if not has_contact:
            markers.append("缺联系方式")
        if not has_evidence:
            markers.append("缺来源证据")
        return markers

    @staticmethod
    def core_gate_status(
        *,
        source_url: str | None,
        has_evidence: bool,
        source_risk_level: str | ChannelRiskLevel | None,
        recommended_grade: str | CustomerGrade,
        review_status: str | StagingReviewStatus,
        queue_status: str | StagingQueueStatus,
    ) -> dict:
        reasons: list[str] = []
        grade = CustomerGrade(recommended_grade)
        review = StagingReviewStatus(review_status)
        queue = StagingQueueStatus(queue_status)
        risk = ChannelRiskLevel(source_risk_level or ChannelRiskLevel.LOW)

        if not (source_url or "").strip():
            reasons.append("缺少来源链接")
        if not has_evidence:
            reasons.append("缺少来源证据")
        if risk == ChannelRiskLevel.FORBIDDEN:
            reasons.append("Forbidden 来源不得作为客户晋级关键来源")
        if (
            review == StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION
            or (risk == ChannelRiskLevel.HIGH and review != StagingReviewStatus.APPROVED)
        ):
            reasons.append("High 来源需完成 Low/Medium 二次复核")
        if grade == CustomerGrade.INVALID:
            reasons.append("Invalid 不得进入 core 或触达队列")
        if grade == CustomerGrade.WATCH:
            reasons.append("Watch 不得进入 core 或触达队列")
        if queue in {StagingQueueStatus.NOT_ELIGIBLE, StagingQueueStatus.BLOCKED}:
            reasons.append("当前队列状态不可晋级")

        return {
            "status": "blocked" if reasons else "ready",
            "can_promote_to_core": not reasons,
            "reasons": reasons or ["来源和证据满足进入 core 的最低要求"],
        }

    @classmethod
    def validate_promote_allowed(cls, **kwargs) -> dict:
        return cls.core_gate_status(**kwargs)

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

    @classmethod
    def build_core_customer_payload(cls, lead: StagingLead, *, existing_customer=None) -> dict:
        do_not_contact = bool(getattr(existing_customer, "do_not_contact", False))
        return {
            "external_id": cls.core_external_id(lead.id),
            "name": lead.customer_name,
            "normalized_name": lead.customer_name.strip().lower(),
            "country": lead.country,
            "city": lead.city,
            "customer_type": CustomerType(lead.customer_type),
            "grade": CustomerGrade(lead.recommended_grade),
            "status": cls.status_after_promotion(lead.recommended_grade, do_not_contact=do_not_contact).value,
            "do_not_contact": do_not_contact,
            "ai_recommended_grade": CustomerGrade(lead.recommended_grade),
            "ai_recommendation_reason": lead.recommended_reason,
            "missing_fields": ", ".join(str(item) for item in (lead.missing_fields or [])),
            "requires_compliance_review": CustomerGrade(lead.recommended_grade) == CustomerGrade.C,
        }

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
    def build_contact_method_payloads(cls, lead: StagingLead, *, source_url: str, evidence_note: str) -> list[dict]:
        payloads: list[dict] = []
        for index, contact in enumerate(lead.contacts_json or []):
            if not isinstance(contact, dict):
                continue
            value = str(contact.get("value") or "").strip()
            if not value:
                continue
            payloads.append(
                {
                    "method_type": cls.normalize_contact_method_type(contact.get("type") or contact.get("method_type")).value,
                    "value": value,
                    "label": contact.get("usage") or contact.get("label"),
                    "source_url": source_url,
                    "evidence_note": evidence_note,
                    "is_primary": index == 0,
                }
            )
        return payloads

    def auto_promote_if_eligible(self, lead: StagingLead, *, actor: str = "auto-promote-agent") -> dict:
        candidate = lead.candidate_url
        source_url = candidate.url if candidate is not None else None
        latest_snapshot = self.latest_page_snapshot_for_lead(lead)
        evidence_note = (lead.source_evidence or "").strip() or (
            latest_snapshot.evidence_note if latest_snapshot is not None else ""
        ).strip()
        risk_level = candidate.source_risk_level if candidate is not None else ChannelRiskLevel.LOW
        grade = CustomerGrade(lead.recommended_grade)

        reasons: list[str] = []
        if not self.has_valid_customer_name(lead.customer_name):
            reasons.append("客户名为空或 Unknown")
        if not self.has_contact(lead.contacts_json):
            reasons.append("缺少联系方式")
        if not evidence_note:
            reasons.append("缺少来源证据")
        if not (source_url or "").strip():
            reasons.append("缺少来源链接")
        if risk_level not in {ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM}:
            reasons.append("仅 Low/Medium 来源允许自动晋级")
        if grade in {CustomerGrade.INVALID, CustomerGrade.WATCH}:
            reasons.append("Invalid/Watch 不自动晋级")

        if reasons:
            return {"promoted": False, "reasons": reasons, "customer": None, "review_log": None, "compliance_review": None}

        original_review_status = lead.review_status
        original_queue_status = lead.queue_status
        original_updated_at = lead.updated_at
        lead.review_status = StagingReviewStatus.APPROVED
        lead.updated_at = datetime.utcnow()

        try:
            result = self.promote_staging_lead_to_core(
                lead_id=lead.id,
                actor=actor,
                review_result="approved",
                review_note="系统自动晋级：客户名、联系方式、来源证据和 Low/Medium 风险准入均满足。",
            )
        except ValueError as exc:
            lead.review_status = original_review_status
            lead.queue_status = original_queue_status
            lead.updated_at = original_updated_at
            return {
                "promoted": False,
                "reasons": [str(exc)],
                "customer": None,
                "review_log": None,
                "compliance_review": None,
            }

        result["promoted"] = True
        result["reasons"] = ["已自动晋级 core"]
        return result

    @staticmethod
    def review_filter_presets() -> dict[str, dict]:
        return {
            "pending_review": {"review_status": StagingReviewStatus.PENDING_REVIEW.value},
            "bc": {"recommended_grade": [CustomerGrade.B.value, CustomerGrade.C.value]},
            "high_secondary": {
                "source_risk_level": ChannelRiskLevel.HIGH.value,
                "requires_secondary_verification": True,
            },
            "missing_contact": {"has_contact": False},
            "watch_invalid": {"recommended_grade": [CustomerGrade.WATCH.value, CustomerGrade.INVALID.value]},
        }

    def create_staging_lead(
        self,
        *,
        candidate_url_id: UUID | str | None,
        customer_name: str | None,
        country: str | None,
        city: str | None,
        customer_type: str | CustomerType | None,
        contacts_json: list | None,
        activity_level: str | None,
        scale_signal: str | None,
        import_used_car_relevance: str | None,
        source_evidence: str | None,
        recommended_grade: str | CustomerGrade,
        recommended_reason: str | None,
        missing_fields: list | None,
        source_risk_level: str | ChannelRiskLevel,
    ) -> StagingLead:
        self.validate_candidate_url_id(candidate_url_id)
        grade = CustomerGrade(recommended_grade)
        payload = self.normalize_payload(
            customer_name=customer_name,
            country=country,
            city=city,
            contacts_json=contacts_json,
            missing_fields=missing_fields,
        )
        staging_lead = StagingLead(
            candidate_url_id=UUID(str(candidate_url_id)),
            customer_name=payload["customer_name"],
            country=payload["country"],
            city=payload["city"],
            customer_type=CustomerType(customer_type or CustomerType.UNKNOWN),
            contacts_json=payload["contacts_json"],
            activity_level=activity_level,
            scale_signal=scale_signal,
            import_used_car_relevance=import_used_car_relevance,
            source_evidence=source_evidence,
            recommended_grade=grade,
            recommended_reason=recommended_reason,
            missing_fields=payload["missing_fields"],
            review_status=self.default_review_status(source_risk_level),
            queue_status=self.default_queue_status(grade),
            dedupe_key=self.build_dedupe_key(payload["customer_name"], payload["city"], payload["contacts_json"]),
            requires_compliance_review=self.default_requires_compliance_review(grade),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(staging_lead)
        self.session.flush()
        return staging_lead

    def list_staging_leads(
        self,
        *,
        review_status: str | StagingReviewStatus | None = None,
        recommended_grade: str | CustomerGrade | list[str] | list[CustomerGrade] | None = None,
        queue_status: str | StagingQueueStatus | None = None,
        source_risk_level: str | ChannelRiskLevel | None = None,
        has_contact: bool | None = None,
        requires_secondary_verification: bool | None = None,
        limit: int = 100,
    ) -> list[StagingLead]:
        statement = (
            select(StagingLead)
            .options(selectinload(StagingLead.candidate_url))
            .join(CandidateUrl)
            .order_by(StagingLead.created_at.desc())
        )
        if review_status is not None:
            statement = statement.where(StagingLead.review_status == StagingReviewStatus(review_status))
        if recommended_grade is not None:
            grades = recommended_grade if isinstance(recommended_grade, list) else [recommended_grade]
            statement = statement.where(StagingLead.recommended_grade.in_([CustomerGrade(grade) for grade in grades]))
        if queue_status is not None:
            statement = statement.where(StagingLead.queue_status == StagingQueueStatus(queue_status))
        if source_risk_level is not None:
            statement = statement.where(CandidateUrl.source_risk_level == ChannelRiskLevel(source_risk_level))
        if requires_secondary_verification is not None:
            statement = statement.where(CandidateUrl.requires_secondary_verification.is_(requires_secondary_verification))

        if has_contact is None:
            return list(self.session.scalars(statement.limit(limit)).unique().all())

        leads = list(self.session.scalars(statement).unique().all())
        if has_contact is not None:
            leads = [lead for lead in leads if self.has_contact(lead.contacts_json) is has_contact]
        return leads[:limit]

    def get_staging_lead(self, lead_id: UUID) -> StagingLead | None:
        return self.session.get(StagingLead, lead_id)

    def latest_page_snapshot_for_lead(self, lead: StagingLead) -> PageSnapshot | None:
        statement = (
            select(PageSnapshot)
            .where(PageSnapshot.candidate_url_id == lead.candidate_url_id)
            .order_by(PageSnapshot.captured_at.desc(), PageSnapshot.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def latest_ai_audit_for_lead(self, lead: StagingLead) -> AIAuditLog | None:
        source_url = lead.candidate_url.url if lead.candidate_url is not None else None
        if not source_url:
            return None
        statement = (
            select(AIAuditLog)
            .where(or_(AIAuditLog.source_url == source_url, cast(AIAuditLog.source_urls, JSONB).contains([source_url])))
            .order_by(AIAuditLog.executed_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def duplicate_signals_for_lead(self, lead: StagingLead) -> dict:
        keys = self.build_duplicate_keys(lead)
        source_url = lead.candidate_url.url if lead.candidate_url is not None else None
        contact_values = [
            self.normalize_contact_value(item.get("value"))
            for item in (lead.contacts_json or [])
            if isinstance(item, dict) and self.normalize_contact_value(item.get("value"))
        ]
        strong_candidates: list[dict] = []
        suspected_candidates: list[dict] = []
        source_candidates: list[dict] = []

        if contact_values:
            customer_rows = self.session.execute(
                select(Customer, ContactMethod)
                .join(ContactMethod, ContactMethod.customer_id == Customer.id)
                .where(
                    Customer.external_id != self.core_external_id(lead.id),
                    func.lower(Customer.normalized_name) == keys["normalized_name"],
                    func.lower(ContactMethod.value).in_(contact_values),
                )
            ).all()
            for customer, contact in customer_rows:
                strong_candidates.append(
                    {
                        "target_type": "core_customer",
                        "target_id": str(customer.id),
                        "reason": f"同名同联系方式：{contact.value}",
                        "source_url": None,
                        "evidence_note": customer.do_not_contact_reason if customer.do_not_contact else None,
                    }
                )

        staging_rows = self.session.scalars(
            select(StagingLead).where(
                StagingLead.id != lead.id,
                func.lower(StagingLead.customer_name) == keys["normalized_name"],
            )
        ).all()
        for other in staging_rows:
            other_keys = self.build_duplicate_keys(other)
            if keys["strong_key"] and keys["strong_key"] == other_keys["strong_key"]:
                strong_candidates.append(
                    {
                        "target_type": "staging_lead",
                        "target_id": str(other.id),
                        "reason": "同名同联系方式",
                        "source_url": other.candidate_url.url if other.candidate_url is not None else None,
                        "evidence_note": other.source_evidence,
                    }
                )
            elif keys["suspected_key"] and keys["suspected_key"] == other_keys["suspected_key"]:
                suspected_candidates.append(
                    {
                        "target_type": "staging_lead",
                        "target_id": str(other.id),
                        "reason": "同名同城市同来源域名",
                        "source_url": other.candidate_url.url if other.candidate_url is not None else None,
                        "evidence_note": other.source_evidence,
                    }
                )

        if source_url:
            lead_sources = self.session.scalars(select(LeadSource)).all()
            for source in lead_sources:
                if self.source_url_hash(source.source_url) == keys["source_url_hash"]:
                    source_candidates.append(
                        {
                            "target_type": "lead_source",
                            "target_id": str(source.id),
                            "reason": "来源URL hash重复",
                            "source_url": source.source_url,
                            "evidence_note": source.evidence_note,
                        }
                    )

        return self.build_duplicate_signal_summary(
            strong_candidates=strong_candidates,
            suspected_candidates=suspected_candidates,
            source_candidates=source_candidates,
        )

    def resolve_duplicate(
        self,
        *,
        lead_id: UUID,
        actor: str,
        action: str,
        target_customer_id: UUID | None = None,
        note: str | None = None,
    ) -> dict:
        lead = self.get_staging_lead(lead_id)
        if lead is None:
            raise ValueError("staging lead not found")
        candidate = lead.candidate_url
        if candidate is not None:
            Phase3ComplianceGuardService.ensure_source_can_be_promotion_key_evidence(
                candidate.source_risk_level,
                session=self.session,
                actor=actor,
                target_ref=f"staging:{lead.id}",
            )
        latest_snapshot = self.latest_page_snapshot_for_lead(lead)
        source_url = candidate.url if candidate is not None else ""
        evidence_note = (lead.source_evidence or "").strip() or (
            latest_snapshot.evidence_note if latest_snapshot is not None else ""
        ).strip()

        if action == "merge_to_core":
            if target_customer_id is None:
                raise ValueError("合并重复线索必须指定 target_customer_id。")
            target_customer = self.session.get(Customer, target_customer_id)
            if target_customer is None:
                raise ValueError("目标 core customer 不存在。")
            payload = self.build_merge_resolution_payload(
                lead,
                target_customer_id=target_customer.id,
                actor=actor,
                source_url=source_url,
                evidence_note=evidence_note,
            )
            source_external_id = f"merge:{lead.id}:{target_customer.id}"
            source = self.session.scalar(select(LeadSource).where(LeadSource.external_id == source_external_id))
            if source is None:
                source = LeadSource(external_id=source_external_id, customer_id=target_customer.id)
                self.session.add(source)
            source.customer_id = target_customer.id
            source.platform = candidate.source_platform if candidate is not None else SourcePlatform.OTHER
            source.source_url = source_url
            source.source_title = latest_snapshot.page_title if latest_snapshot is not None else None
            source.evidence_note = evidence_note
            source.evidence_excerpt = None
            source.channel_risk_level = candidate.source_risk_level if candidate is not None else ChannelRiskLevel.LOW
            source.collected_by = actor
            for contact_payload in self.build_contact_method_payloads(lead, source_url=source_url, evidence_note=evidence_note):
                method_type = ContactMethodType(contact_payload["method_type"])
                exists = self.session.scalar(
                    select(ContactMethod).where(
                        ContactMethod.customer_id == target_customer.id,
                        ContactMethod.method_type == method_type,
                        ContactMethod.value == contact_payload["value"],
                    )
                )
                if exists is None:
                    self.session.add(
                        ContactMethod(
                            customer_id=target_customer.id,
                            method_type=method_type,
                            value=contact_payload["value"],
                            label=contact_payload["label"],
                            source_url=source_url,
                            evidence_note=evidence_note,
                            is_primary=False,
                        )
                    )
        elif action == "mark_duplicate":
            payload = {
                "review_status": StagingReviewStatus.DUPLICATE.value,
                "queue_status": StagingQueueStatus.NOT_ELIGIBLE.value,
                "review_log": {
                    "task_id": str(lead.id),
                    "action": "mark_duplicate_staging_lead",
                    "reviewer": actor,
                    "input_ref": f"staging:{lead.id}",
                    "output_ref": None,
                    "result": "duplicate",
                },
            }
        elif action == "dismiss":
            payload = {
                "review_status": StagingReviewStatus.PENDING_REVIEW.value,
                "queue_status": StagingQueueStatus.PENDING_REVIEW.value,
                "review_log": {
                    "task_id": str(lead.id),
                    "action": "dismiss_duplicate_signal",
                    "reviewer": actor,
                    "input_ref": f"staging:{lead.id}",
                    "output_ref": None,
                    "result": "dismissed",
                },
            }
        else:
            raise ValueError("不支持的重复处理动作。")

        lead.review_status = StagingReviewStatus(payload["review_status"])
        lead.queue_status = StagingQueueStatus(payload["queue_status"])
        lead.updated_at = datetime.utcnow()
        log_payload = payload["review_log"]
        review_log = ReviewLog(
            task_id=log_payload["task_id"],
            agent_name="manual-review",
            action=log_payload["action"],
            reviewer=log_payload["reviewer"],
            input_ref=log_payload["input_ref"],
            output_ref=log_payload["output_ref"],
            result=log_payload["result"],
            error_message=note,
        )
        self.session.add(review_log)
        self.session.flush()
        return {
            "lead": lead,
            "review_log": review_log,
            "target_customer_id": target_customer_id,
            "action": action,
        }

    def promote_staging_lead_to_core(
        self,
        *,
        lead_id: UUID,
        actor: str,
        review_result: str,
        review_note: str | None = None,
    ) -> dict:
        if review_result != "approved":
            raise ValueError("只有人工复核通过的 staging 线索可以晋级 core。")
        lead = self.get_staging_lead(lead_id)
        if lead is None:
            raise ValueError("staging lead not found")
        candidate = lead.candidate_url
        latest_snapshot = self.latest_page_snapshot_for_lead(lead)
        source_url = candidate.url if candidate is not None else None
        evidence_note = (lead.source_evidence or "").strip() or (
            latest_snapshot.evidence_note if latest_snapshot is not None else ""
        ).strip()
        gate = self.validate_promote_allowed(
            source_url=source_url,
            has_evidence=bool(evidence_note),
            source_risk_level=candidate.source_risk_level if candidate is not None else None,
            recommended_grade=lead.recommended_grade,
            review_status=lead.review_status,
            queue_status=lead.queue_status,
        )
        if not gate["can_promote_to_core"]:
            raise ValueError("；".join(gate["reasons"]))
        self.raise_if_strong_duplicate(self.duplicate_signals_for_lead(lead))

        external_id = self.core_external_id(lead.id)
        customer = self.session.scalar(select(Customer).where(Customer.external_id == external_id))
        payload = self.build_core_customer_payload(lead, existing_customer=customer)
        if customer is None:
            customer = Customer(external_id=external_id, name=payload["name"])
            self.session.add(customer)

        customer.name = payload["name"]
        customer.normalized_name = payload["normalized_name"]
        customer.country = payload["country"]
        customer.city = payload["city"]
        customer.customer_type = payload["customer_type"]
        customer.grade = payload["grade"]
        customer.status = CustomerStatus(payload["status"])
        customer.do_not_contact = payload["do_not_contact"]
        customer.ai_recommended_grade = payload["ai_recommended_grade"]
        customer.ai_recommendation_reason = payload["ai_recommendation_reason"]
        customer.missing_fields = payload["missing_fields"]
        customer.owner = actor
        customer.updated_at = datetime.utcnow()
        self.session.flush()

        source = self.session.scalar(select(LeadSource).where(LeadSource.external_id == external_id))
        if source is None:
            source = LeadSource(external_id=external_id, customer_id=customer.id)
            self.session.add(source)
        source.customer_id = customer.id
        source.platform = candidate.source_platform if candidate is not None else SourcePlatform.OTHER
        source.source_url = source_url or ""
        source.source_title = latest_snapshot.page_title if latest_snapshot is not None else None
        source.evidence_note = evidence_note
        source.evidence_excerpt = None
        source.channel_risk_level = candidate.source_risk_level if candidate is not None else ChannelRiskLevel.LOW
        source.collected_by = actor

        for contact_payload in self.build_contact_method_payloads(lead, source_url=source_url or "", evidence_note=evidence_note):
            method_type = ContactMethodType(contact_payload["method_type"])
            exists = self.session.scalar(
                select(ContactMethod).where(
                    ContactMethod.customer_id == customer.id,
                    ContactMethod.method_type == method_type,
                    ContactMethod.value == contact_payload["value"],
                )
            )
            if exists is None:
                self.session.add(
                    ContactMethod(
                        customer_id=customer.id,
                        method_type=method_type,
                        value=contact_payload["value"],
                        label=contact_payload["label"],
                        source_url=contact_payload["source_url"],
                        evidence_note=contact_payload["evidence_note"],
                        is_primary=contact_payload["is_primary"],
                    )
                )

        compliance_review = None
        if payload["requires_compliance_review"]:
            compliance_review = self.session.scalar(
                select(ComplianceReview)
                .where(ComplianceReview.customer_id == customer.id)
                .order_by(ComplianceReview.created_at.desc(), ComplianceReview.id.desc())
            )
            if compliance_review is None:
                compliance_review = ComplianceReview(
                    customer_id=customer.id,
                    status=ComplianceReviewStatus.PENDING,
                    reason="C级线索晋级 core 后，报价/合同前必须合规复核。",
                    risk_note="待复核贸易、支付、物流、清关风险。",
                )
                self.session.add(compliance_review)

        lead.review_status = StagingReviewStatus.APPROVED
        lead.queue_status = StagingQueueStatus.ELIGIBLE
        lead.updated_at = datetime.utcnow()
        review_log = ReviewLog(
            task_id=str(lead.id),
            agent_name="manual-review",
            action="promote_staging_to_core",
            reviewer=actor,
            input_ref=f"staging:{lead.id}",
            output_ref=f"customer:{customer.id}",
            result=review_result,
            error_message=review_note,
        )
        self.session.add(review_log)
        self.session.flush()
        return {
            "customer": customer,
            "review_log": review_log,
            "compliance_review": compliance_review,
            "requires_compliance_review": payload["requires_compliance_review"],
        }
