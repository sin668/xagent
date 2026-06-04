from dataclasses import dataclass, field
from datetime import datetime

from app.models.enums import (
    ChannelRiskLevel,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    SourcePlatform,
)
from app.services.feishu_client import FeishuRecord


SUPPORTED_OBJECTS = ["客户线索", "渠道来源", "车源报价", "触达记录", "话术库"]


@dataclass(frozen=True)
class MappedCustomerLead:
    external_id: str
    name: str
    country: str
    city: str | None
    customer_type: str
    grade: str
    status: str
    owner: str | None
    do_not_contact: bool
    do_not_contact_reason: str | None
    do_not_contact_marked_by: str | None
    do_not_contact_marked_at: datetime | None
    source_url: str
    source_platform: str
    source_evidence_note: str
    channel_risk_level: str
    contact_methods: list[dict[str, str]] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MappingResult:
    object_name: str
    external_id: str
    valid: bool
    payload: dict[str, object] | MappedCustomerLead | None = None
    errors: list[str] = field(default_factory=list)


CUSTOMER_TYPE_MAP = {
    "当地车商/二级经销商": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
    "个人买家": CustomerType.PERSONAL_BUYER.value,
    "KOL/汽车博主": CustomerType.KOL_AUTO_BLOGGER.value,
    "未知": CustomerType.UNKNOWN.value,
    "非目标": CustomerType.NON_TARGET.value,
}

CUSTOMER_STATUS_MAP = {
    "新采集": CustomerStatus.NEW.value,
    "待补全": CustomerStatus.NEEDS_ENRICHMENT.value,
    "待复核": CustomerStatus.PENDING_REVIEW.value,
    "可交付客服": CustomerStatus.READY_FOR_CUSTOMER_SERVICE.value,
    "客服跟进中": CustomerStatus.CUSTOMER_SERVICE_FOLLOWING.value,
    "可交付销售": CustomerStatus.READY_FOR_SALES.value,
    "销售跟进中": CustomerStatus.SALES_FOLLOWING.value,
    "无效/暂不匹配": CustomerStatus.INVALID.value,
    "沉淀观察": CustomerStatus.WATCH.value,
    "拒绝联系/勿扰": CustomerStatus.DO_NOT_CONTACT.value,
}

GRADE_VALUES = {grade.value for grade in CustomerGrade}
RISK_VALUES = {risk.value for risk in ChannelRiskLevel}
SOURCE_PLATFORM_MAP = {
    "官网": SourcePlatform.OFFICIAL_WEBSITE.value,
    "公开目录": SourcePlatform.PUBLIC_DIRECTORY.value,
    "搜索引擎": SourcePlatform.SEARCH_ENGINE.value,
    "地图": SourcePlatform.YANDEX_MAPS.value,
    "Google 地图结果": SourcePlatform.GOOGLE_MAPS.value,
    "Yandex 地图结果": SourcePlatform.YANDEX_MAPS.value,
    "YouTube": SourcePlatform.YOUTUBE.value,
    "Drom": SourcePlatform.DROM.value,
}


def normalize_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"是", "true", "yes", "1", "y"}


def as_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def split_missing_fields(value: object) -> list[str]:
    text = as_text(value)
    if not text:
        return []
    return [part.strip() for part in text.replace("、", ",").split(",") if part.strip()]


def parse_datetime(value: object) -> datetime | None:
    text = as_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def map_customer_lead(record: FeishuRecord) -> MappingResult:
    fields = record.fields
    errors: list[str] = []
    external_id = as_text(fields.get("线索ID")) or record.record_id
    name = as_text(fields.get("客户名称"))
    country = as_text(fields.get("国家")) or "Russia"
    city = as_text(fields.get("城市/地区"))
    source_url = as_text(fields.get("来源链接"))
    evidence = as_text(fields.get("来源证据备注"))
    grade = as_text(fields.get("线索等级")) or "Watch"
    status_text = as_text(fields.get("线索状态")) or "待复核"
    risk = as_text(fields.get("渠道风险等级")) or "High"

    if not name:
        errors.append("客户名称缺失")
    if not source_url:
        errors.append("来源链接缺失")
    if not evidence:
        errors.append("来源证据备注缺失")
    if grade not in GRADE_VALUES:
        errors.append(f"线索等级非法: {grade}")
    if risk not in RISK_VALUES:
        errors.append(f"渠道风险等级非法: {risk}")

    contact_methods: list[dict[str, str]] = []
    for field_name, method_type in [
        ("邮箱", ContactMethodType.EMAIL.value),
        ("电话", ContactMethodType.PHONE.value),
        ("WhatsApp", ContactMethodType.WHATSAPP.value),
        ("Telegram", ContactMethodType.TELEGRAM.value),
        ("官网", ContactMethodType.WEBSITE.value),
    ]:
        value = as_text(fields.get(field_name))
        if value and value != "Unknown":
            contact_methods.append({"method_type": method_type, "value": value})

    if errors:
        return MappingResult(object_name="客户线索", external_id=external_id, valid=False, errors=errors)

    payload = MappedCustomerLead(
        external_id=external_id,
        name=name or "Unknown",
        country=country,
        city=city,
        customer_type=CUSTOMER_TYPE_MAP.get(as_text(fields.get("客户类型")) or "未知", CustomerType.UNKNOWN.value),
        grade=grade,
        status=CustomerStatus.DO_NOT_CONTACT.value if normalize_bool(fields.get("是否勿扰")) else CUSTOMER_STATUS_MAP.get(status_text, CustomerStatus.PENDING_REVIEW.value),
        owner=as_text(fields.get("负责人")),
        do_not_contact=normalize_bool(fields.get("是否勿扰")),
        do_not_contact_reason=as_text(fields.get("勿扰原因")),
        do_not_contact_marked_by=as_text(fields.get("勿扰标记人")),
        do_not_contact_marked_at=parse_datetime(fields.get("勿扰标记时间")),
        source_url=source_url or "",
        source_platform=SOURCE_PLATFORM_MAP.get(as_text(fields.get("来源平台")) or "", SourcePlatform.OTHER.value),
        source_evidence_note=evidence or "",
        channel_risk_level=risk,
        contact_methods=contact_methods,
        missing_fields=split_missing_fields(fields.get("缺失信息")),
    )
    return MappingResult(object_name="客户线索", external_id=external_id, valid=True, payload=payload)


def map_channel_risk(record: FeishuRecord) -> MappingResult:
    fields = record.fields
    external_id = as_text(fields.get("渠道ID")) or record.record_id
    risk = as_text(fields.get("风险等级")) or as_text(fields.get("初始风险等级")) or "High"
    errors = []
    if risk not in RISK_VALUES:
        errors.append(f"风险等级非法: {risk}")
    name = as_text(fields.get("平台/渠道名称"))
    if not name:
        errors.append("平台/渠道名称缺失")
    payload = {
        "external_id": external_id,
        "channel_name": name,
        "channel_type": as_text(fields.get("渠道类型")) or "其他",
        "risk_level": risk,
        "collection_allowed": normalize_bool(fields.get("是否进入 PoC")) or risk in {"Low", "Medium"},
        "allowed_actions": as_text(fields.get("允许动作")) or "Unknown",
        "forbidden_actions": as_text(fields.get("禁止动作")) or "Unknown",
        "policy_source_url": as_text(fields.get("政策来源")),
    }
    return MappingResult("渠道来源", external_id, not errors, payload if not errors else None, errors)


def map_inventory_item(record: FeishuRecord) -> MappingResult:
    fields = record.fields
    external_id = as_text(fields.get("车源ID")) or record.record_id
    errors = []
    if not as_text(fields.get("品牌")):
        errors.append("品牌缺失")
    if not as_text(fields.get("车型")):
        errors.append("车型缺失")
    payload = {
        "external_id": external_id,
        "brand": as_text(fields.get("品牌")),
        "model": as_text(fields.get("车型")),
        "year": fields.get("年份"),
        "mileage_km": fields.get("里程"),
        "condition_summary": as_text(fields.get("车况")) or as_text(fields.get("配置摘要")),
        "quoted_price": fields.get("价格"),
        "currency": as_text(fields.get("币种")) or "USD",
        "quote_status": as_text(fields.get("价格确认状态")) or "待确认",
        "export_ready": as_text(fields.get("可出口状态")) == "可出口",
    }
    return MappingResult("车源报价", external_id, not errors, payload if not errors else None, errors)


def map_outreach_record(record: FeishuRecord) -> MappingResult:
    fields = record.fields
    external_id = as_text(fields.get("触达ID")) or record.record_id
    errors = []
    if not as_text(fields.get("关联客户")):
        errors.append("关联客户缺失")
    payload = {
        "external_id": external_id,
        "customer_ref": as_text(fields.get("关联客户")),
        "customer_name_snapshot": as_text(fields.get("客户名称快照")),
        "channel": as_text(fields.get("触达渠道")) or "其他",
        "risk_level": as_text(fields.get("渠道风险等级")) or "High",
        "script_version": as_text(fields.get("话术版本")),
        "sent_by": as_text(fields.get("发送人")),
        "sent_at": parse_datetime(fields.get("发送时间")),
        "status": as_text(fields.get("触达状态")) or "未发送",
        "response_summary": as_text(fields.get("回复摘要")),
        "next_action": as_text(fields.get("下一步动作")),
        "triggers_do_not_contact": normalize_bool(fields.get("是否触发勿扰")),
        "do_not_contact_reason": as_text(fields.get("勿扰原因")),
    }
    return MappingResult("触达记录", external_id, not errors, payload if not errors else None, errors)


def map_script_template(record: FeishuRecord) -> MappingResult:
    fields = record.fields
    external_id = as_text(fields.get("话术ID")) or record.record_id
    errors = []
    for required in ["话术名称", "中文内部版", "俄语客户版", "版本号", "拒绝联系路径"]:
        if not as_text(fields.get(required)):
            errors.append(f"{required}缺失")
    payload = {
        "external_id": external_id,
        "name": as_text(fields.get("话术名称")),
        "script_type": as_text(fields.get("话术类型")) or "其他",
        "applicable_grades": as_text(fields.get("适用等级")) or "Unknown",
        "applicable_channels": as_text(fields.get("适用渠道")) or "Unknown",
        "chinese_internal_text": as_text(fields.get("中文内部版")),
        "russian_customer_text": as_text(fields.get("俄语客户版")),
        "forbidden_promises": as_text(fields.get("禁止承诺点")) or "Unknown",
        "review_status": as_text(fields.get("审核状态")) or "草稿",
        "version": as_text(fields.get("版本号")),
        "opt_out_path": as_text(fields.get("拒绝联系路径")),
        "risk_note": as_text(fields.get("风险提示")),
    }
    return MappingResult("话术库", external_id, not errors, payload if not errors else None, errors)


MAPPERS = {
    "客户线索": map_customer_lead,
    "渠道来源": map_channel_risk,
    "车源报价": map_inventory_item,
    "触达记录": map_outreach_record,
    "话术库": map_script_template,
}
