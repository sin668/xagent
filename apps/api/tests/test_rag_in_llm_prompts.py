from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import (
    AITaskType,
    ChannelRiskLevel,
    CustomerGrade,
    KnowledgeItemStatus,
    KnowledgeReviewStatus,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.services.llm_lead_grading import LLMLeadGradingService
from app.services.rag_prompt_context import RAGPromptContextService
from app.services.outreach_draft import OutreachDraftService


def fake_item(
    *,
    title: str,
    body: str,
    collection_name: str,
    language: str = "zh",
    country: str = "Russia",
    channels: list[str] | None = None,
    status=KnowledgeItemStatus.ACTIVE,
    review_status=KnowledgeReviewStatus.APPROVED,
):
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        body=body,
        language=language,
        country=country,
        applicable_channels=channels or [],
        status=status,
        review_status=review_status,
        collection=SimpleNamespace(name=collection_name),
        source_ref=f"docs/poc/{collection_name}.md",
        version="v1",
    )


def test_extraction_rag_context_only_includes_approved_active_knowledge() -> None:
    approved = fake_item(
        title="公开目录采集 SOP",
        body="只允许读取公开页面，禁止登录后批量采集。",
        collection_name="channel_sop",
        channels=["official_website"],
    )
    draft = fake_item(
        title="未审核关键词",
        body="不应进入 prompt",
        collection_name="keyword_library",
        channels=["official_website"],
        review_status=KnowledgeReviewStatus.PENDING,
    )
    deprecated = fake_item(
        title="废弃 SOP",
        body="不应进入 prompt",
        collection_name="channel_sop",
        channels=["official_website"],
        status=KnowledgeItemStatus.DEPRECATED,
    )

    context = RAGPromptContextService.build_context_from_items(
        [approved, draft, deprecated],
        task_type=AITaskType.LEAD_EXTRACTION,
        query="公开页面 车商",
        country="Russia",
        channel="official_website",
        language="zh",
    )

    assert context["context_status"] == "ready"
    assert [item["title"] for item in context["knowledge_item_refs"]] == ["公开目录采集 SOP"]
    assert "禁止登录后批量采集" in context["context_text"]
    assert "未审核关键词" not in context["context_text"]
    assert "废弃 SOP" not in context["context_text"]
    assert context["hard_rule_boundary"] == "RAG 仅作为 LLM 上下文，合规硬规则必须由规则服务执行。"


def test_empty_rag_context_is_auditable_and_does_not_block_prompt() -> None:
    context = RAGPromptContextService.build_context_from_items(
        [],
        task_type=AITaskType.LEAD_GRADING,
        query="unknown dealer",
        country="Russia",
        channel="maps",
        language="zh",
    )

    assert context["context_status"] == "empty_context"
    assert context["knowledge_item_refs"] == []
    assert context["context_text"] == ""


def test_grading_audit_input_contains_rag_refs_and_hard_rules_still_override_llm() -> None:
    rag_context = RAGPromptContextService.build_context_from_items(
        [
            fake_item(
                title="C 级合规复核规则",
                body="C 级线索报价或合同前必须合规复核。",
                collection_name="compliance_rules",
                channels=["maps"],
            )
        ],
        task_type=AITaskType.LEAD_GRADING,
        query="C grade compliance",
        country="Russia",
        channel="maps",
        language="zh",
    )
    audit_input = LLMLeadGradingService.build_grading_audit_input(
        staging_lead_id=uuid4(),
        source_url="https://dealer.example/contact",
        do_not_contact=False,
        rag_context=rag_context,
    )

    result = LLMLeadGradingService.apply_hard_rules(
        {
            "recommended_grade": CustomerGrade.C.value,
            "touch_queue_allowed": True,
            "compliance_review_required": False,
            "next_action": "handoff_to_export_sales",
            "suggested_handoff_team": "export_sales",
            "risk_flags": [],
            "evidence_refs": [
                {
                    "claim": "dealer_signal",
                    "evidence_text": "cars with mileage",
                    "source_url": "https://dealer.example/contact",
                }
            ],
        },
        source_risk_level=ChannelRiskLevel.MEDIUM,
        review_status=StagingReviewStatus.PENDING_REVIEW,
        has_evidence=True,
        has_contact=True,
        do_not_contact=False,
    )

    assert audit_input["rag_context"]["context_status"] == "ready"
    assert audit_input["rag_context"]["knowledge_item_refs"][0]["collection"] == "compliance_rules"
    assert result.queue_status == StagingQueueStatus.ELIGIBLE
    assert result.requires_compliance_review is True
    assert "c_grade_requires_compliance_review" in result.risk_flags


def test_outreach_draft_audit_can_carry_approved_rag_template_refs() -> None:
    rag_context = RAGPromptContextService.build_context_from_items(
        [
            fake_item(
                title="俄语拒绝联系路径模板",
                body="Если вы хотите отказаться от связи, сообщите нам...",
                collection_name="script_template",
                channels=["email"],
                language="ru",
            ),
            fake_item(
                title="未审核 FAQ",
                body="不应进入外发话术上下文",
                collection_name="faq",
                channels=["email"],
                language="ru",
                review_status=KnowledgeReviewStatus.PENDING,
            ),
        ],
        task_type=AITaskType.OUTREACH_DRAFT,
        query="отказаться от связи",
        country="Russia",
        channel="email",
        language="ru",
    )

    draft = OutreachDraftService().get_existing_draft(customer_id=uuid4(), rag_context=rag_context)

    assert draft["audit"]["rag_context"]["context_status"] == "ready"
    assert [item["collection"] for item in draft["audit"]["rag_context"]["knowledge_item_refs"]] == ["script_template"]
    assert "未审核 FAQ" not in draft["audit"]["rag_context"]["context_text"]
