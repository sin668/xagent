from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.models import CandidateUrl, CollectionTask, ComplianceReview, ContactMethod, Customer, LeadSource, ReviewLog, StagingLead
from app.models.enums import (
    ChannelRiskLevel,
    CollectionTaskStatus,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    SourcePlatform,
    SourceUsageType,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.schemas.staging_leads import StagingPromoteRequest
from app.services.staging_leads import StagingLeadService


API_ROOT = Path(__file__).resolve().parents[1]
TEST_PREFIX = "TEST-AUTO-PROMOTE-"


async def cleanup_auto_promote_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def cleanup(sync_session):
            test_source_customer_ids = list(
                sync_session.scalars(
                    select(LeadSource.customer_id).where(LeadSource.source_url.like("https://auto-promote.example/%"))
                ).all()
            )
            prefixed_customer_ids = list(
                sync_session.scalars(
                    select(Customer.id).where(Customer.name.like(f"{TEST_PREFIX}%"))
                ).all()
            )
            target_customer_ids = list(dict.fromkeys([*test_source_customer_ids, *prefixed_customer_ids]))
            if target_customer_ids:
                sync_session.execute(delete(ContactMethod).where(ContactMethod.customer_id.in_(target_customer_ids)))
                sync_session.execute(delete(LeadSource).where(LeadSource.customer_id.in_(target_customer_ids)))
                sync_session.execute(delete(ComplianceReview).where(ComplianceReview.customer_id.in_(target_customer_ids)))
                sync_session.execute(delete(Customer).where(Customer.id.in_(target_customer_ids)))

            candidate_ids = list(
                sync_session.scalars(
                    select(CandidateUrl.id).where(CandidateUrl.url.like(f"https://auto-promote.example/%"))
                ).all()
            )
            if candidate_ids:
                sync_session.execute(delete(StagingLead).where(StagingLead.candidate_url_id.in_(candidate_ids)))
                sync_session.execute(delete(CandidateUrl).where(CandidateUrl.id.in_(candidate_ids)))

            task_ids = list(
                sync_session.scalars(
                    select(CollectionTask.id).where(CollectionTask.channel_name.like(f"{TEST_PREFIX}%"))
                ).all()
            )
            if task_ids:
                sync_session.execute(delete(CollectionTask).where(CollectionTask.id.in_(task_ids)))
            sync_session.execute(delete(ReviewLog).where(ReviewLog.task_id.like(f"{TEST_PREFIX}%")))

        await async_session.run_sync(cleanup)
        await async_session.commit()


async def run_with_session(callback):
    async with AsyncSessionLocal() as async_session:
        result = await async_session.run_sync(callback)
        await async_session.commit()
        return result


@pytest_asyncio.fixture(autouse=True)
async def isolated_auto_promote_records():
    await cleanup_auto_promote_records()
    yield
    await cleanup_auto_promote_records()


def create_candidate(session, *, url_suffix: str, risk_level: ChannelRiskLevel = ChannelRiskLevel.LOW) -> CandidateUrl:
    task = CollectionTask(
        task_type="lead_extraction",
        channel_name=f"{TEST_PREFIX}{url_suffix}",
        risk_level=risk_level,
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
        max_sample_size=10,
        allowed_actions="仅公开网页读取，不自动触达。",
        forbidden_actions="不登录、不绕过反爬、不自动私信。",
        status=CollectionTaskStatus.PENDING,
    )
    session.add(task)
    session.flush()
    candidate = CandidateUrl(
        task_id=task.id,
        url=f"https://auto-promote.example/{url_suffix}",
        url_hash=StagingLeadService.source_url_hash(f"https://auto-promote.example/{url_suffix}"),
        source_platform=SourcePlatform.OFFICIAL_WEBSITE,
        source_risk_level=risk_level,
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
        requires_secondary_verification=risk_level == ChannelRiskLevel.HIGH,
        queue_eligible=risk_level in {ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM},
        discovery_reason="测试公开官网来源。",
    )
    session.add(candidate)
    session.flush()
    return candidate


def test_promote_api_contract_exists() -> None:
    api_text = (API_ROOT / "app" / "api" / "staging_leads.py").read_text(encoding="utf-8")

    assert '@router.post("/{lead_id:uuid}/promote"' in api_text
    assert "StagingPromoteRequest" in api_text
    assert "promote_staging_lead_to_core" in api_text


def test_promote_request_requires_actor_and_review_result() -> None:
    request = StagingPromoteRequest(actor="ops-anna", review_result="approved", review_note="证据完整")

    assert request.actor == "ops-anna"
    assert request.review_result == "approved"
    assert request.review_note == "证据完整"


def test_validate_promote_allowed_blocks_missing_source_evidence_high_and_watch() -> None:
    gate = StagingLeadService.validate_promote_allowed(
        source_url="",
        has_evidence=False,
        source_risk_level=ChannelRiskLevel.HIGH,
        recommended_grade=CustomerGrade.WATCH,
        review_status=StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION,
        queue_status=StagingQueueStatus.NOT_ELIGIBLE,
    )

    assert gate["can_promote_to_core"] is False
    assert "缺少来源链接" in gate["reasons"]
    assert "缺少来源证据" in gate["reasons"]
    assert "High 来源需完成 Low/Medium 二次复核" in gate["reasons"]
    assert "Watch 不得进入 core 或触达队列" in gate["reasons"]


def test_promote_mapping_preserves_staging_reference_and_dnc_status() -> None:
    lead_id = uuid4()
    lead = SimpleNamespace(
        id=lead_id,
        customer_name="Auto City Moscow",
        country="Russia",
        city="Moscow",
        customer_type="local_dealer_secondary_dealer",
        recommended_grade=CustomerGrade.C,
        recommended_reason="公开证据完整，已有进口二手相关性。",
        missing_fields=["月采购量"],
        contacts_json=[{"type": "email", "value": "sales@example.ru", "usage": "人工邮件触达"}],
    )
    existing_customer = SimpleNamespace(do_not_contact=True, status="do_not_contact")

    payload = StagingLeadService.build_core_customer_payload(lead, existing_customer=existing_customer)
    contacts = StagingLeadService.build_contact_method_payloads(
        lead,
        source_url="https://dealer.example.ru",
        evidence_note="官网公开展示邮箱。",
    )

    assert payload["external_id"] == f"staging:{lead_id}"
    assert payload["do_not_contact"] is True
    assert payload["status"] == "do_not_contact"
    assert payload["requires_compliance_review"] is True
    assert contacts == [
        {
            "method_type": "email",
            "value": "sales@example.ru",
            "label": "人工邮件触达",
            "source_url": "https://dealer.example.ru",
            "evidence_note": "官网公开展示邮箱。",
            "is_primary": True,
        }
    ]


@pytest.mark.asyncio
async def test_auto_promote_eligible_staging_lead_writes_customer_source_and_contact() -> None:
    def act(session):
        candidate = create_candidate(session, url_suffix="eligible-low", risk_level=ChannelRiskLevel.LOW)
        service = StagingLeadService(session)
        lead = service.create_staging_lead(
            candidate_url_id=candidate.id,
            customer_name=f"{TEST_PREFIX}Auto City Moscow",
            country="Russia",
            city="Moscow",
            customer_type="local_dealer_secondary_dealer",
            contacts_json=[{"type": "telegram", "value": "@autocity_test", "usage": "公开 Telegram"}],
            activity_level="active",
            scale_signal="公开页面展示多个二手车库存。",
            import_used_car_relevance="high",
            source_evidence="官网公开页面展示二手车库存和 Telegram 联系方式。",
            recommended_grade=CustomerGrade.C,
            recommended_reason="有公开联系方式和二手车经营信号。",
            missing_fields=[],
            source_risk_level=candidate.source_risk_level,
        )
        result = service.auto_promote_if_eligible(lead, actor="auto-promote-agent")
        customer = result["customer"]
        contact = session.scalar(select(ContactMethod).where(ContactMethod.customer_id == customer.id))
        source = session.scalar(select(LeadSource).where(LeadSource.customer_id == customer.id))
        compliance = session.scalar(select(ComplianceReview).where(ComplianceReview.customer_id == customer.id))
        return lead, customer, contact, source, compliance

    lead, customer, contact, source, compliance = await run_with_session(act)

    assert customer.name == f"{TEST_PREFIX}Auto City Moscow"
    assert customer.status == CustomerStatus.READY_FOR_SALES
    assert customer.grade == CustomerGrade.C
    assert contact.method_type == ContactMethodType.TELEGRAM
    assert contact.value == "@autocity_test"
    assert source.source_url == "https://auto-promote.example/eligible-low"
    assert source.evidence_note == "官网公开页面展示二手车库存和 Telegram 联系方式。"
    assert compliance is not None
    assert lead.review_status == StagingReviewStatus.APPROVED
    assert lead.queue_status == StagingQueueStatus.ELIGIBLE


@pytest.mark.asyncio
async def test_auto_promote_skips_watch_invalid_high_and_missing_contact_or_evidence() -> None:
    def act(session):
        service = StagingLeadService(session)
        cases = [
            ("watch", ChannelRiskLevel.LOW, CustomerGrade.WATCH, "证据", [{"type": "email", "value": "watch@example.test"}]),
            ("invalid", ChannelRiskLevel.LOW, CustomerGrade.INVALID, "证据", [{"type": "email", "value": "invalid@example.test"}]),
            ("high", ChannelRiskLevel.HIGH, CustomerGrade.B, "证据", [{"type": "email", "value": "high@example.test"}]),
            ("missing-contact", ChannelRiskLevel.LOW, CustomerGrade.B, "证据", []),
            ("missing-evidence", ChannelRiskLevel.LOW, CustomerGrade.B, "", [{"type": "email", "value": "missing@example.test"}]),
            ("unknown-name", ChannelRiskLevel.LOW, CustomerGrade.B, "证据", [{"type": "email", "value": "unknown@example.test"}]),
        ]
        results = []
        for suffix, risk, grade, evidence, contacts in cases:
            candidate = create_candidate(session, url_suffix=suffix, risk_level=risk)
            lead = service.create_staging_lead(
                candidate_url_id=candidate.id,
                customer_name="Unknown" if suffix == "unknown-name" else f"{TEST_PREFIX}{suffix}",
                country="Russia",
                city="Moscow",
                customer_type="local_dealer_secondary_dealer",
                contacts_json=contacts,
                activity_level="active",
                scale_signal="测试",
                import_used_car_relevance="medium",
                source_evidence=evidence,
                recommended_grade=grade,
                recommended_reason="测试",
                missing_fields=[],
                source_risk_level=candidate.source_risk_level,
            )
            results.append(service.auto_promote_if_eligible(lead, actor="auto-promote-agent"))
        customer_count = session.scalar(select(func.count()).select_from(Customer).where(Customer.name.like(f"{TEST_PREFIX}%")))
        return results, customer_count

    results, customer_count = await run_with_session(act)

    assert [item["promoted"] for item in results] == [False, False, False, False, False, False]
    assert customer_count == 0
