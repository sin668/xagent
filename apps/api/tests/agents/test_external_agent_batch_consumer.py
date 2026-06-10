from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import (
    CandidateUrl,
    CollectionTask,
    ComplianceReview,
    ContactMethod,
    Customer,
    LeadCleanupRun,
    LeadCleanupSuggestion,
    LeadEnrichmentFieldCandidate,
    LeadEnrichmentResult,
    LeadSource,
    PageSnapshot,
    ReviewLog,
    StagingLead,
)
from app.models.enums import (
    CandidateUrlStatus,
    ChannelRiskLevel,
    CollectionTaskStatus,
    CustomerGrade,
    CustomerType,
    SourcePlatform,
    SourceUsageType,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.services.external_agent_batch_consumer import ExternalAgentBatchConsumer
from app.services.staging_leads import StagingLeadService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    for model in (
        CollectionTask,
        CandidateUrl,
        PageSnapshot,
        StagingLead,
        LeadEnrichmentResult,
        LeadEnrichmentFieldCandidate,
        Customer,
        LeadSource,
        ContactMethod,
        ReviewLog,
        ComplianceReview,
        LeadCleanupRun,
        LeadCleanupSuggestion,
    ):
        model.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal()


def add_staging_lead(session, *, grade=CustomerGrade.B, name="Auto City") -> StagingLead:
    task = CollectionTask(
        channel_name="official",
        task_type="test",
        risk_level=ChannelRiskLevel.LOW,
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
        allowed_actions="read_public_source_only",
        forbidden_actions="no_auto_outreach,no_login,no_anti_scraping_bypass",
        status=CollectionTaskStatus.COMPLETED,
    )
    session.add(task)
    session.flush()
    candidate = CandidateUrl(
        task_id=task.id,
        url=f"https://{name.lower().replace(' ', '-')}.example",
        url_hash=str(uuid4()),
        source_platform=SourcePlatform.OFFICIAL_WEBSITE,
        source_risk_level=ChannelRiskLevel.LOW,
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
        discovery_reason="公开官网。",
        status=CandidateUrlStatus.STAGED,
    )
    session.add(candidate)
    session.flush()
    lead = StagingLead(
        candidate_url_id=candidate.id,
        customer_name=name,
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        contacts_json=[],
        source_evidence="公开官网展示车商名称和联系入口。",
        recommended_grade=grade,
        recommended_reason="测试线索。",
        missing_fields=["contacts_json"],
        review_status=StagingReviewStatus.PENDING_REVIEW,
        queue_status=StagingQueueStatus.PENDING_REVIEW,
        requires_compliance_review=False,
    )
    session.add(lead)
    session.flush()
    return lead


def deep_enrichment_response(lead: StagingLead) -> dict:
    output = {
        "schema_version": "phase3.agent.deep_enrichment.v1",
        "agent_run_id": str(uuid4()),
        "staging_lead_id": str(lead.id),
        "field_candidates": [
            {
                "field_name": "contacts_json",
                "candidate_value": [{"type": "email", "value": "sales@auto-city.example"}],
                "source_type": "ai_public_source",
                "source_url": "https://auto-city.example/contact",
                "evidence_note": "公开联系页展示 sales@auto-city.example。",
                "confidence_score": 0.9,
                "review_status": "pending",
            }
        ],
        "missing_fields": [],
        "recommended_next_action": "manual_review",
        "audit": {"writes_core_tables": False},
    }
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": str(uuid4()),
        "request_id": str(uuid4()),
        "status": "succeeded",
        "agent_type": "deep_enrichment",
        "agent_mode": "active",
        "audit": {"writes_core_tables": False},
        "output": {"batch_results": [{"status": "succeeded", "staging_lead_id": str(lead.id), "output": output}]},
    }


def deep_enrichment_contact_merge_response(lead: StagingLead) -> dict:
    output = {
        "schema_version": "phase3.agent.deep_enrichment.v1",
        "agent_run_id": str(uuid4()),
        "staging_lead_id": str(lead.id),
        "field_candidates": [
            {
                "field_name": "contacts_json",
                "candidate_value": [
                    {"type": "email", "value": "sales@merge.example", "usage": "AI 深挖公开来源"}
                ],
                "source_type": "ai_public_source",
                "source_url": "https://merge.example/contact",
                "evidence_note": "公开联系页展示 sales@merge.example。",
                "confidence_score": 0.88,
                "review_status": "pending",
            }
        ],
        "missing_fields": [],
        "recommended_next_action": "manual_review",
        "audit": {"writes_core_tables": False},
    }
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": str(uuid4()),
        "request_id": str(uuid4()),
        "status": "succeeded",
        "agent_type": "deep_enrichment",
        "agent_mode": "active",
        "audit": {"writes_core_tables": False},
        "output": {"batch_results": [{"status": "succeeded", "staging_lead_id": str(lead.id), "output": output}]},
    }


def deep_enrichment_empty_response(lead: StagingLead) -> dict:
    output = {
        "schema_version": "phase3.agent.deep_enrichment.v1",
        "agent_run_id": str(uuid4()),
        "staging_lead_id": str(lead.id),
        "field_candidates": [],
        "missing_fields": ["customer_name", "contacts_json", "country", "city", "source_evidence"],
        "recommended_next_action": "mark_invalid",
        "audit": {"writes_core_tables": False},
    }
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": str(uuid4()),
        "request_id": str(uuid4()),
        "status": "succeeded",
        "agent_type": "deep_enrichment",
        "agent_mode": "active",
        "audit": {"writes_core_tables": False},
        "output": {"batch_results": [{"status": "succeeded", "staging_lead_id": str(lead.id), "output": output}]},
    }


def lead_cleanup_response(watch: StagingLead, invalid: StagingLead) -> dict:
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": str(uuid4()),
        "request_id": str(uuid4()),
        "status": "succeeded",
        "agent_type": "lead_cleanup",
        "agent_mode": "active",
        "audit": {"writes_core_tables": False},
        "output": {
            "schema_version": "phase3.agent.lead_cleanup.v1",
            "cleanup_run_id": str(uuid4()),
            "suggestions": [
                {
                    "staging_lead_id": str(watch.id),
                    "suggestion_type": "needs_manual_review",
                    "target_lead_id": None,
                    "confidence_score": 0.82,
                    "reason": "公开证据恢复，建议升级为 B。",
                    "evidence_json": {"restored_grade": "B", "source": "公开邮箱可核验"},
                    "recommended_action": "升级为 B 级线索",
                    "review_status": "pending",
                },
                {
                    "staging_lead_id": str(invalid.id),
                    "suggestion_type": "confirm_invalid",
                    "target_lead_id": None,
                    "confidence_score": 0.9,
                    "reason": "无目标客户证据，确认无效。",
                    "evidence_json": {"invalid_reason": "non_target"},
                    "recommended_action": "确认无效并隐藏",
                    "review_status": "pending",
                },
            ],
            "blocked_items": [],
            "audit": {"writes_core_tables": False},
        },
    }


def lead_cleanup_manual_review_response(low_quality: StagingLead) -> dict:
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": str(uuid4()),
        "request_id": str(uuid4()),
        "status": "succeeded",
        "agent_type": "lead_cleanup",
        "agent_mode": "active",
        "audit": {"writes_core_tables": False},
        "output": {
            "schema_version": "phase3.agent.lead_cleanup.v1",
            "cleanup_run_id": str(uuid4()),
            "suggestions": [
                {
                    "staging_lead_id": str(low_quality.id),
                    "suggestion_type": "needs_manual_review",
                    "target_lead_id": None,
                    "confidence_score": 0.61,
                    "reason": "信息不足，建议人工复核。",
                    "evidence_json": {"quality": "low"},
                    "recommended_action": "保持观察",
                    "review_status": "pending",
                }
            ],
            "blocked_items": [],
            "audit": {"writes_core_tables": False},
        },
    }


def test_consume_deep_enrichment_batch_updates_staging_and_auto_promotes_customer() -> None:
    engine, session = make_session()
    try:
        lead = add_staging_lead(session, grade=CustomerGrade.B)

        result = ExternalAgentBatchConsumer(session).consume_deep_enrichment_response(deep_enrichment_response(lead))
        session.commit()

        refreshed = session.get(StagingLead, lead.id)
        customers = list(session.scalars(select(Customer)).all())
        contacts = list(session.scalars(select(ContactMethod)).all())
        assert result["processed_count"] == 1
        assert result["promoted_count"] == 1
        assert refreshed.contacts_json == [{"type": "email", "value": "sales@auto-city.example"}]
        assert refreshed.review_status == StagingReviewStatus.APPROVED
        assert len(customers) == 1
        assert contacts[0].value == "sales@auto-city.example"
    finally:
        session.close()
        engine.dispose()


def test_consume_deep_enrichment_merges_contact_candidates_into_existing_contacts() -> None:
    engine, session = make_session()
    try:
        lead = add_staging_lead(session, grade=CustomerGrade.B, name="Merge Dealer")
        lead.contacts_json = [{"type": "phone", "value": "+7 999 000 00 00", "usage": "原始电话"}]
        session.flush()

        result = ExternalAgentBatchConsumer(session).consume_deep_enrichment_response(deep_enrichment_contact_merge_response(lead))
        session.commit()

        refreshed = session.get(StagingLead, lead.id)
        assert result["field_candidate_count"] == 1
        assert refreshed.contacts_json == [
            {"type": "phone", "value": "+7 999 000 00 00", "usage": "原始电话"},
            {"type": "email", "value": "sales@merge.example", "usage": "AI 深挖公开来源"},
        ]
    finally:
        session.close()
        engine.dispose()


def test_consume_deep_enrichment_keeps_low_quality_lead_status_when_no_effective_fields() -> None:
    engine, session = make_session()
    try:
        low_quality = add_staging_lead(session, grade=CustomerGrade.B, name="Unknown")
        low_quality.customer_name = "Unknown"
        low_quality.country = "Unknown"
        low_quality.city = None
        low_quality.contacts_json = []
        low_quality.source_evidence = None
        low_quality.missing_fields = ["customer_name", "contacts_json", "country", "city", "source_evidence"]
        original_grade = low_quality.recommended_grade
        original_review_status = low_quality.review_status
        original_queue_status = low_quality.queue_status
        session.flush()

        result = ExternalAgentBatchConsumer(session).consume_deep_enrichment_response(deep_enrichment_empty_response(low_quality))
        session.commit()

        refreshed = session.get(StagingLead, low_quality.id)
        assert result["quality_invalidated_count"] == 0
        assert result["promoted_count"] == 0
        assert result["items"][0]["quality_reasons"] == [
            "缺客户名称",
            "缺至少一个联系方式",
            "缺国家",
            "缺城市",
            "缺来源证据",
        ]
        assert refreshed.recommended_grade == original_grade
        assert refreshed.review_status == original_review_status
        assert refreshed.queue_status == original_queue_status
        assert refreshed.recommended_grade == CustomerGrade.B
    finally:
        session.close()
        engine.dispose()


def test_consume_lead_cleanup_batch_hides_invalid_and_upgrades_watch() -> None:
    engine, session = make_session()
    try:
        watch = add_staging_lead(session, grade=CustomerGrade.WATCH, name="Watch Dealer")
        watch.contacts_json = [{"type": "email", "value": "watch@example.com"}]
        invalid = add_staging_lead(session, grade=CustomerGrade.INVALID, name="Invalid Dealer")
        session.flush()

        result = ExternalAgentBatchConsumer(session).consume_lead_cleanup_response(lead_cleanup_response(watch, invalid))
        session.commit()

        watch = session.get(StagingLead, watch.id)
        invalid = session.get(StagingLead, invalid.id)
        assert result["executed_count"] == 2
        assert result["upgraded_count"] == 1
        assert result["hidden_count"] == 1
        assert watch.recommended_grade == CustomerGrade.B
        assert watch.queue_status == StagingQueueStatus.PENDING_REVIEW
        assert invalid.recommended_grade == CustomerGrade.INVALID
        assert invalid.review_status == StagingReviewStatus.REJECTED
        assert invalid.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    finally:
        session.close()
        engine.dispose()


def test_consume_lead_cleanup_auto_invalidates_low_quality_watch_even_when_llm_keeps_manual_review() -> None:
    engine, session = make_session()
    try:
        low_quality = add_staging_lead(session, grade=CustomerGrade.WATCH, name="Unknown")
        low_quality.customer_name = "Unknown"
        low_quality.country = "Unknown"
        low_quality.city = None
        low_quality.contacts_json = []
        low_quality.source_evidence = None
        low_quality.missing_fields = ["customer_name", "contacts_json", "country", "city", "source_evidence", "do_not_contact"]
        session.flush()

        result = ExternalAgentBatchConsumer(session).consume_lead_cleanup_response(
            lead_cleanup_manual_review_response(low_quality)
        )
        session.commit()

        refreshed = session.get(StagingLead, low_quality.id)
        assert result["hidden_count"] == 1
        assert result["quality_invalidated_count"] == 1
        assert refreshed.recommended_grade == CustomerGrade.INVALID
        assert refreshed.review_status == StagingReviewStatus.REJECTED
        assert refreshed.queue_status == StagingQueueStatus.NOT_ELIGIBLE
        assert "质量过低" in refreshed.recommended_reason
    finally:
        session.close()
        engine.dispose()


def test_list_staging_leads_excludes_hidden_rejected_duplicate_and_not_eligible_by_default() -> None:
    engine, session = make_session()
    try:
        visible = add_staging_lead(session, grade=CustomerGrade.B, name="Visible Dealer")
        visible_watch = add_staging_lead(session, grade=CustomerGrade.WATCH, name="Visible Watch")
        hidden_invalid = add_staging_lead(session, grade=CustomerGrade.INVALID, name="Hidden Invalid")
        hidden_invalid.review_status = StagingReviewStatus.REJECTED
        hidden_invalid.queue_status = StagingQueueStatus.NOT_ELIGIBLE
        hidden_duplicate = add_staging_lead(session, grade=CustomerGrade.WATCH, name="Hidden Duplicate")
        hidden_duplicate.review_status = StagingReviewStatus.DUPLICATE
        hidden_duplicate.queue_status = StagingQueueStatus.NOT_ELIGIBLE
        hidden_blocked = add_staging_lead(session, grade=CustomerGrade.B, name="Hidden Blocked")
        hidden_blocked.queue_status = StagingQueueStatus.BLOCKED
        session.flush()

        leads = StagingLeadService(session).list_staging_leads(limit=100)

        assert {lead.id for lead in leads} == {visible.id, visible_watch.id}
    finally:
        session.close()
        engine.dispose()
