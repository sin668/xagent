from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ChannelRiskRule,
    ContactMethod,
    Customer,
    InventoryItem,
    LeadSource,
    OutreachRecord,
    ScriptTemplate,
    SyncLog,
)
from app.models.enums import (
    ChannelRiskLevel,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    OutreachStatus,
    ScriptReviewStatus,
    SyncStatus,
)
from app.services.feishu_client import FeishuClient
from app.services.feishu_mapping import MAPPERS, SUPPORTED_OBJECTS, MappedCustomerLead, MappingResult


@dataclass
class ObjectSyncResult:
    object_name: str
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class SyncRunResult:
    status: str
    dry_run: bool
    results: list[ObjectSyncResult]


class FeishuSyncService:
    def __init__(self, client: FeishuClient, session: Session | None = None) -> None:
        self.client = client
        self.session = session

    def sync(self, object_names: list[str] | None = None, dry_run: bool = True) -> SyncRunResult:
        names = object_names or SUPPORTED_OBJECTS
        results = [self._sync_object(name, dry_run=dry_run) for name in names]
        if any(result.failure_count for result in results):
            status = "partial" if any(result.success_count for result in results) else "failed"
        else:
            status = "success"
        return SyncRunResult(status=status, dry_run=dry_run, results=results)

    def _sync_object(self, object_name: str, dry_run: bool) -> ObjectSyncResult:
        result = ObjectSyncResult(object_name=object_name)
        mapper = MAPPERS.get(object_name)
        if mapper is None:
            result.failure_count += 1
            result.errors.append(f"Unsupported sync object: {object_name}")
            if not dry_run and self.session is not None:
                self._record_sync_log(result)
            return result

        try:
            records = self.client.list_records(object_name)
        except Exception as exc:
            result.failure_count += 1
            result.errors.append(f"{object_name} fetch failed: {exc}")
            if not dry_run and self.session is not None:
                self._record_sync_log(result)
            return result

        mapped_records = [mapper(record) for record in records]
        for mapped in mapped_records:
            self._apply_mapping_result(result, mapped, dry_run=dry_run)
        if not dry_run and self.session is not None:
            self._record_sync_log(result)
        return result

    def _apply_mapping_result(self, result: ObjectSyncResult, mapped: MappingResult, dry_run: bool) -> None:
        if not mapped.valid:
            result.failure_count += 1
            result.errors.extend([f"{mapped.external_id}: {error}" for error in mapped.errors])
            return

        if dry_run:
            result.success_count += 1
            return

        if self.session is None:
            result.failure_count += 1
            result.errors.append(f"{mapped.external_id}: database session is required when dry_run is false")
            return

        try:
            self._upsert_mapped_record(mapped)
        except Exception as exc:
            result.failure_count += 1
            result.errors.append(f"{mapped.external_id}: database write failed: {exc}")
            return

        result.success_count += 1

    def _upsert_mapped_record(self, mapped: MappingResult) -> None:
        if self.session is None or mapped.payload is None:
            raise RuntimeError("database session and payload are required")
        if mapped.object_name == "客户线索":
            self._upsert_customer_lead(mapped.payload)
        elif mapped.object_name == "渠道来源":
            self._upsert_channel_risk(mapped.payload)
        elif mapped.object_name == "车源报价":
            self._upsert_inventory_item(mapped.payload)
        elif mapped.object_name == "触达记录":
            self._upsert_outreach_record(mapped.payload)
        elif mapped.object_name == "话术库":
            self._upsert_script_template(mapped.payload)
        else:
            raise ValueError(f"unsupported object: {mapped.object_name}")

    def _upsert_customer_lead(self, payload: MappedCustomerLead) -> None:
        assert self.session is not None
        customer = self.session.scalar(select(Customer).where(Customer.external_id == payload.external_id))
        if customer is None:
            customer = Customer(external_id=payload.external_id, name=payload.name)
            self.session.add(customer)

        customer.name = payload.name
        customer.normalized_name = payload.name.strip().lower()
        customer.country = payload.country
        customer.city = payload.city
        customer.customer_type = CustomerType(payload.customer_type)
        customer.grade = CustomerGrade(payload.grade)
        customer.status = CustomerStatus(payload.status)
        customer.owner = payload.owner
        customer.do_not_contact = payload.do_not_contact
        customer.do_not_contact_reason = payload.do_not_contact_reason
        customer.do_not_contact_marked_by = payload.do_not_contact_marked_by
        customer.do_not_contact_marked_at = payload.do_not_contact_marked_at
        customer.missing_fields = ", ".join(payload.missing_fields)

        self.session.flush()

        source = self.session.scalar(select(LeadSource).where(LeadSource.external_id == payload.external_id))
        if source is None:
            source = LeadSource(external_id=payload.external_id, customer_id=customer.id)
            self.session.add(source)
        source.customer_id = customer.id
        source.platform = payload.source_platform
        source.source_url = payload.source_url
        source.evidence_note = payload.source_evidence_note
        source.channel_risk_level = ChannelRiskLevel(payload.channel_risk_level)

        for contact in payload.contact_methods:
            method_type = ContactMethodType(contact["method_type"])
            value = contact["value"]
            exists = self.session.scalar(
                select(ContactMethod).where(
                    ContactMethod.customer_id == customer.id,
                    ContactMethod.method_type == method_type,
                    ContactMethod.value == value,
                )
            )
            if exists is None:
                self.session.add(
                    ContactMethod(
                        customer_id=customer.id,
                        method_type=method_type,
                        value=value,
                        source_url=payload.source_url,
                        evidence_note=payload.source_evidence_note,
                    )
                )

    def _upsert_channel_risk(self, payload: dict[str, object]) -> None:
        assert self.session is not None
        rule = self.session.scalar(select(ChannelRiskRule).where(ChannelRiskRule.external_id == payload["external_id"]))
        if rule is None:
            rule = ChannelRiskRule(external_id=str(payload["external_id"]), channel_name=str(payload["channel_name"]))
            self.session.add(rule)
        rule.channel_name = str(payload["channel_name"])
        rule.channel_type = str(payload["channel_type"])
        rule.risk_level = ChannelRiskLevel(str(payload["risk_level"]))
        rule.collection_allowed = bool(payload["collection_allowed"])
        rule.ai_processing_allowed = rule.risk_level in {ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM}
        rule.allowed_actions = str(payload["allowed_actions"])
        rule.forbidden_actions = str(payload["forbidden_actions"])
        rule.policy_source_url = payload.get("policy_source_url") and str(payload["policy_source_url"])

    def _upsert_inventory_item(self, payload: dict[str, object]) -> None:
        assert self.session is not None
        item = self.session.scalar(select(InventoryItem).where(InventoryItem.external_id == payload["external_id"]))
        if item is None:
            item = InventoryItem(external_id=str(payload["external_id"]), brand=str(payload["brand"]), model=str(payload["model"]))
            self.session.add(item)
        item.brand = str(payload["brand"])
        item.model = str(payload["model"])
        item.year = int(payload["year"]) if payload.get("year") not in (None, "") else None
        item.mileage_km = int(payload["mileage_km"]) if payload.get("mileage_km") not in (None, "") else None
        item.condition_summary = payload.get("condition_summary") and str(payload["condition_summary"])
        item.quoted_price = payload.get("quoted_price")
        item.currency = str(payload["currency"])
        item.quote_status = str(payload["quote_status"])
        item.export_ready = bool(payload["export_ready"])

    def _upsert_outreach_record(self, payload: dict[str, object]) -> None:
        assert self.session is not None
        customer_ref = str(payload["customer_ref"])
        customer = self.session.scalar(select(Customer).where(Customer.external_id == customer_ref))
        if customer is None:
            raise ValueError(f"关联客户不存在: {customer_ref}")
        record = self.session.scalar(select(OutreachRecord).where(OutreachRecord.external_id == payload["external_id"]))
        if record is None:
            record = OutreachRecord(external_id=str(payload["external_id"]), customer_id=customer.id)
            self.session.add(record)
        record.customer_id = customer.id
        record.channel = self._map_outreach_channel(str(payload["channel"]))
        record.status = self._map_outreach_status(str(payload["status"]))
        record.script_version = payload.get("script_version") and str(payload["script_version"])
        record.sent_by = payload.get("sent_by") and str(payload["sent_by"])
        record.sent_at = payload.get("sent_at")
        record.response_summary = payload.get("response_summary") and str(payload["response_summary"])
        record.next_action = payload.get("next_action") and str(payload["next_action"])
        record.triggers_do_not_contact = bool(payload["triggers_do_not_contact"])
        record.do_not_contact_reason = payload.get("do_not_contact_reason") and str(payload["do_not_contact_reason"])
        if record.triggers_do_not_contact:
            customer.do_not_contact = True
            customer.do_not_contact_reason = record.do_not_contact_reason
            customer.status = CustomerStatus.DO_NOT_CONTACT

    def _upsert_script_template(self, payload: dict[str, object]) -> None:
        assert self.session is not None
        script = self.session.scalar(select(ScriptTemplate).where(ScriptTemplate.external_id == payload["external_id"]))
        if script is None:
            script = ScriptTemplate(external_id=str(payload["external_id"]), name=str(payload["name"]))
            self.session.add(script)
        script.name = str(payload["name"])
        script.script_type = str(payload["script_type"])
        script.applicable_grades = str(payload["applicable_grades"])
        script.applicable_channels = str(payload["applicable_channels"])
        script.chinese_internal_text = str(payload["chinese_internal_text"])
        script.russian_customer_text = str(payload["russian_customer_text"])
        script.forbidden_promises = str(payload["forbidden_promises"])
        script.review_status = self._map_script_review_status(str(payload["review_status"]))
        script.version = str(payload["version"])
        script.opt_out_path = str(payload["opt_out_path"])
        script.risk_note = payload.get("risk_note") and str(payload["risk_note"])

    def _record_sync_log(self, result: ObjectSyncResult) -> None:
        assert self.session is not None
        status = SyncStatus.SUCCESS
        if result.failure_count and result.success_count:
            status = SyncStatus.PARTIAL
        elif result.failure_count:
            status = SyncStatus.FAILED
        self.session.add(
            SyncLog(
                object_name=result.object_name,
                status=status,
                success_count=result.success_count,
                failure_count=result.failure_count,
                error_summary="\n".join(result.errors) if result.errors else None,
                metadata_json={"skipped_count": result.skipped_count},
                finished_at=datetime.utcnow(),
            )
        )

    @staticmethod
    def _map_outreach_channel(value: str) -> ContactMethodType:
        mapping = {
            "Email": ContactMethodType.EMAIL,
            "官网表单": ContactMethodType.WEBSITE_FORM,
            "电话": ContactMethodType.PHONE,
            "WhatsApp": ContactMethodType.WHATSAPP,
            "Telegram": ContactMethodType.TELEGRAM,
            "VK": ContactMethodType.VKONTAKTE,
        }
        return mapping.get(value, ContactMethodType.OTHER)

    @staticmethod
    def _map_outreach_status(value: str) -> OutreachStatus:
        mapping = {
            "未发送": OutreachStatus.DRAFT,
            "已发送": OutreachStatus.SENT,
            "已回复": OutreachStatus.REPLIED,
            "拒绝": OutreachStatus.REJECTED,
            "无回复": OutreachStatus.SENT,
            "错误联系方式": OutreachStatus.CLOSED,
        }
        return mapping.get(value, OutreachStatus.DRAFT)

    @staticmethod
    def _map_script_review_status(value: str) -> ScriptReviewStatus:
        mapping = {
            "草稿": ScriptReviewStatus.DRAFT,
            "待业务审核": ScriptReviewStatus.BUSINESS_REVIEW,
            "待合规审核": ScriptReviewStatus.COMPLIANCE_REVIEW,
            "可外发": ScriptReviewStatus.APPROVED_FOR_EXTERNAL_USE,
            "停用": ScriptReviewStatus.DISABLED,
        }
        return mapping.get(value, ScriptReviewStatus.DRAFT)
