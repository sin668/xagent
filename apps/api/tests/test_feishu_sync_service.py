from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import AsyncSessionLocal
from app.models import ChannelRiskRule, ContactMethod, Customer, InventoryItem, LeadSource, OutreachRecord, ScriptTemplate, SyncLog
from app.models.enums import CustomerStatus
from app.services.feishu_client import FeishuRecord
from app.services.feishu_mapping import SUPPORTED_OBJECTS, map_customer_lead
from app.services.sync_service import FeishuSyncService


TEST_PREFIX = "TEST-E1S2-"


class FakeFeishuClient:
    def __init__(self, records_by_table: dict[str, list[FeishuRecord]]) -> None:
        self.records_by_table = records_by_table

    def list_records(self, table_name: str) -> list[FeishuRecord]:
        return self.records_by_table.get(table_name, [])


class FailingFeishuClient:
    def list_records(self, table_name: str) -> list[FeishuRecord]:
        raise RuntimeError("boom")


async def cleanup_test_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(ContactMethod).where(ContactMethod.value.like("%example.ru%")))
        for model in [OutreachRecord, LeadSource, Customer, ChannelRiskRule, InventoryItem, ScriptTemplate]:
            await async_session.execute(delete(model).where(model.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def run_with_session(callback):
    async with AsyncSessionLocal() as async_session:
        result = await async_session.run_sync(callback)
        await async_session.commit()
        return result


@pytest_asyncio.fixture(autouse=True)
async def isolated_postgres_records():
    await cleanup_test_records()
    yield
    await cleanup_test_records()


def customer_record(**overrides: object) -> FeishuRecord:
    fields: dict[str, object] = {
        "线索ID": f"{TEST_PREFIX}LEAD-001",
        "客户名称": "Demo Dealer",
        "国家": "Russia",
        "城市/地区": "Moscow",
        "客户类型": "当地车商/二级经销商",
        "线索等级": "B",
        "线索状态": "可交付客服",
        "邮箱": "sales@example.ru",
        "电话": "+7 999 000 0000",
        "Telegram": "@demo_dealer",
        "官网": "https://example.ru",
        "来源平台": "官网",
        "来源链接": "https://example.ru/contact",
        "来源证据备注": "公开官网展示二手车库存和联系方式",
        "渠道风险等级": "Low",
        "负责人": "张三",
        "是否勿扰": "否",
        "勿扰原因": "",
    }
    fields.update(overrides)
    return FeishuRecord(record_id="rec-1", fields=fields)


def channel_risk_record(**overrides: object) -> FeishuRecord:
    fields: dict[str, object] = {
        "渠道ID": f"{TEST_PREFIX}CHANNEL-001",
        "平台/渠道名称": f"{TEST_PREFIX}官网",
        "渠道类型": "官网",
        "风险等级": "Low",
        "是否进入 PoC": "是",
        "允许动作": "人工查看公开页面和记录来源链接",
        "禁止动作": "不得登录后批量采集，不得自动私信",
        "政策来源": "https://example.ru/policy",
    }
    fields.update(overrides)
    return FeishuRecord(record_id="rec-channel-1", fields=fields)


def inventory_record(**overrides: object) -> FeishuRecord:
    fields: dict[str, object] = {
        "车源ID": f"{TEST_PREFIX}CAR-001",
        "品牌": "Toyota",
        "车型": "Camry",
        "年份": "2021",
        "里程": "32000",
        "车况": "二手车，公开报价待确认",
        "价格": "23000",
        "币种": "USD",
        "价格确认状态": "待确认",
        "可出口状态": "可出口",
    }
    fields.update(overrides)
    return FeishuRecord(record_id="rec-inventory-1", fields=fields)


def outreach_record(**overrides: object) -> FeishuRecord:
    fields: dict[str, object] = {
        "触达ID": f"{TEST_PREFIX}OUTREACH-001",
        "关联客户": f"{TEST_PREFIX}LEAD-001",
        "客户名称快照": "Demo Dealer",
        "触达渠道": "Email",
        "渠道风险等级": "Low",
        "话术版本": "v0.1",
        "发送人": "manual-operator",
        "发送时间": "2026-05-28 10:00",
        "触达状态": "未发送",
        "回复摘要": "",
        "下一步动作": "人工复核后触达",
        "是否触发勿扰": "否",
        "勿扰原因": "",
    }
    fields.update(overrides)
    return FeishuRecord(record_id="rec-outreach-1", fields=fields)


def script_template_record(**overrides: object) -> FeishuRecord:
    fields: dict[str, object] = {
        "话术ID": f"{TEST_PREFIX}SCRIPT-001",
        "话术名称": "俄语合作初触达",
        "话术类型": "初次合作",
        "适用等级": "A/B",
        "适用渠道": "Email/官网表单",
        "中文内部版": "说明合作意向，不承诺价格和交付周期。",
        "俄语客户版": "Здравствуйте, мы хотели бы обсудить возможное сотрудничество.",
        "禁止承诺点": "不得承诺最终价格、清关、物流和交付周期",
        "审核状态": "待业务审核",
        "版本号": "v0.1",
        "拒绝联系路径": "客户回复拒绝后标记勿扰",
        "风险提示": "仅供人工审核后使用",
    }
    fields.update(overrides)
    return FeishuRecord(record_id="rec-script-1", fields=fields)


def test_supported_objects_cover_five_feishu_tables() -> None:
    assert SUPPORTED_OBJECTS == ["客户线索", "渠道来源", "车源报价", "触达记录", "话术库"]


def test_customer_mapping_preserves_do_not_contact_status() -> None:
    mapped = map_customer_lead(
        customer_record(
            **{
                "是否勿扰": "是",
                "勿扰原因": "客户拒绝联系",
                "勿扰标记人": "客服A",
                "勿扰标记时间": "2026-05-28 10:30",
            }
        )
    )
    assert mapped.valid is True
    assert mapped.payload is not None
    assert mapped.payload.do_not_contact is True
    assert mapped.payload.status == CustomerStatus.DO_NOT_CONTACT.value
    assert mapped.payload.do_not_contact_reason == "客户拒绝联系"
    assert mapped.payload.do_not_contact_marked_by == "客服A"
    assert mapped.payload.do_not_contact_marked_at is not None


def test_missing_required_fields_are_reported_without_writes() -> None:
    result = map_customer_lead(customer_record(**{"来源链接": ""}))
    assert result.valid is False
    assert "来源链接缺失" in result.errors


@pytest.mark.asyncio
async def test_dry_run_counts_records_without_database_writes() -> None:
    def act(session: Session):
        service = FeishuSyncService(FakeFeishuClient({"客户线索": [customer_record()]}), session=session)
        result = service.sync(["客户线索"], dry_run=True)
        customer = session.scalar(select(Customer).where(Customer.external_id == f"{TEST_PREFIX}LEAD-001"))
        return result, customer

    result, customer = await run_with_session(act)
    assert result.status == "success"
    assert result.results[0].success_count == 1
    assert customer is None


@pytest.mark.asyncio
async def test_customer_sync_writes_customer_source_contacts_and_log() -> None:
    started_at = datetime.utcnow()

    def act(session: Session):
        service = FeishuSyncService(FakeFeishuClient({"客户线索": [customer_record()]}), session=session)
        result = service.sync(["客户线索"], dry_run=False)

        customer = session.scalar(select(Customer).where(Customer.external_id == f"{TEST_PREFIX}LEAD-001"))
        sources = session.scalars(select(LeadSource).where(LeadSource.customer_id == customer.id)).all() if customer else []
        contacts = session.scalars(select(ContactMethod).where(ContactMethod.customer_id == customer.id)).all() if customer else []
        sync_logs = session.scalars(
            select(SyncLog).where(SyncLog.object_name == "客户线索", SyncLog.started_at >= started_at)
        ).all()
        return result, customer, sources, contacts, sync_logs

    result, customer, sources, contacts, sync_logs = await run_with_session(act)
    assert result.status == "success"
    assert customer is not None
    assert customer.do_not_contact is False

    assert len(sources) == 1
    assert sources[0].source_url == "https://example.ru/contact"
    assert {contact.method_type.value for contact in contacts} >= {"email", "phone", "telegram", "website"}
    assert len(sync_logs) >= 1
    assert sync_logs[0].object_name == "客户线索"
    assert sync_logs[0].success_count == 1
    assert sync_logs[0].failure_count == 0


@pytest.mark.asyncio
async def test_customer_sync_preserves_do_not_contact_actor_and_time_from_feishu() -> None:
    record = customer_record(
        **{
            "是否勿扰": "是",
            "勿扰原因": "客户明确拒绝联系",
            "勿扰标记人": "客服A",
            "勿扰标记时间": "2026-05-28 10:30",
        }
    )

    def act(session: Session):
        service = FeishuSyncService(FakeFeishuClient({"客户线索": [record]}), session=session)
        result = service.sync(["客户线索"], dry_run=False)
        customer = session.scalar(select(Customer).where(Customer.external_id == f"{TEST_PREFIX}LEAD-001"))
        return result, customer

    result, customer = await run_with_session(act)

    assert result.status == "success"
    assert customer.do_not_contact is True
    assert customer.do_not_contact_reason == "客户明确拒绝联系"
    assert customer.do_not_contact_marked_by == "客服A"
    assert customer.do_not_contact_marked_at is not None
    assert customer.status == CustomerStatus.DO_NOT_CONTACT


@pytest.mark.asyncio
async def test_sync_writes_all_five_feishu_objects_to_postgres() -> None:
    records = {
        "客户线索": [customer_record()],
        "渠道来源": [channel_risk_record()],
        "车源报价": [inventory_record()],
        "触达记录": [outreach_record()],
        "话术库": [script_template_record()],
    }

    def act(session: Session):
        service = FeishuSyncService(FakeFeishuClient(records), session=session)
        result = service.sync(SUPPORTED_OBJECTS, dry_run=False)
        return {
            "status": result.status,
            "results": [(item.object_name, item.success_count, item.failure_count) for item in result.results],
            "customer": session.scalar(select(Customer).where(Customer.external_id == f"{TEST_PREFIX}LEAD-001")),
            "channel": session.scalar(select(ChannelRiskRule).where(ChannelRiskRule.external_id == f"{TEST_PREFIX}CHANNEL-001")),
            "inventory": session.scalar(select(InventoryItem).where(InventoryItem.external_id == f"{TEST_PREFIX}CAR-001")),
            "outreach": session.scalar(select(OutreachRecord).where(OutreachRecord.external_id == f"{TEST_PREFIX}OUTREACH-001")),
            "script": session.scalar(select(ScriptTemplate).where(ScriptTemplate.external_id == f"{TEST_PREFIX}SCRIPT-001")),
        }

    result = await run_with_session(act)

    assert result["status"] == "success"
    assert result["results"] == [
        ("客户线索", 1, 0),
        ("渠道来源", 1, 0),
        ("车源报价", 1, 0),
        ("触达记录", 1, 0),
        ("话术库", 1, 0),
    ]
    assert result["customer"] is not None
    assert result["channel"] is not None
    assert result["inventory"] is not None
    assert result["outreach"] is not None
    assert result["script"] is not None


@pytest.mark.asyncio
async def test_sync_failure_is_logged_and_does_not_mutate_feishu_client() -> None:
    started_at = datetime.utcnow()
    bad = customer_record(**{"来源链接": ""})
    client = FakeFeishuClient({"客户线索": [bad]})

    def act(session: Session):
        service = FeishuSyncService(client, session=session)
        result = service.sync(["客户线索"], dry_run=False)
        customer = session.scalar(select(Customer).where(Customer.external_id == f"{TEST_PREFIX}LEAD-001"))
        log = session.scalar(select(SyncLog).where(SyncLog.object_name == "客户线索", SyncLog.started_at >= started_at))
        return result, customer, log

    result, customer, log = await run_with_session(act)

    assert result.status == "failed"
    assert result.results[0].failure_count == 1
    assert customer is None
    assert log is not None
    assert log.failure_count == 1
    assert "来源链接缺失" in (log.error_summary or "")


@pytest.mark.asyncio
async def test_fetch_failure_is_logged_when_not_dry_run() -> None:
    started_at = datetime.utcnow()

    def act(session: Session):
        service = FeishuSyncService(FailingFeishuClient(), session=session)
        result = service.sync(["客户线索"], dry_run=False)
        log = session.scalar(select(SyncLog).where(SyncLog.object_name == "客户线索", SyncLog.started_at >= started_at))
        return result, log

    result, log = await run_with_session(act)
    assert result.status == "failed"
    assert log is not None
    assert log.object_name == "客户线索"
    assert log.failure_count == 1
    assert "fetch failed" in (log.error_summary or "")
