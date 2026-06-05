from collections.abc import AsyncIterator
from hmac import compare_digest
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models import Customer, EmailMessage, KnowledgeItem
from app.schemas.knowledge import KnowledgeRetrievalFilterRequest, KnowledgeRetrievalFilterResponse
from app.api.knowledge import serialize_retrieval_filter_result
from app.services.email_reply_auto_send import EmailReplyAutoSendEligibilityInput, EmailReplyAutoSendEligibilityService
from app.services.email_reply_context import EmailReplyContextBuilder
from app.services.email_reply_hard_block import EmailReplyHardBlockInput, EmailReplyHardBlockService
from app.services.knowledge_search import KnowledgeSearchService
from app.settings import settings


AGENTS_API_KEY_HEADER = "X-Agents-Api-Key"
AGENTS_API_KEY_ERROR = "Invalid or missing agents API key"


router = APIRouter(prefix="/internal/email-reply", tags=["internal-email-reply"])


class InternalEmailReplyContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(pattern="^email-reply-v1$")
    request_id: UUID
    draft_id: UUID | None = None
    thread_id: UUID
    message_id: UUID
    customer_id: UUID | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    prompt: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class InternalEmailReplyAutoSendCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(pattern="^email-reply-v1$")
    request_id: UUID
    draft_id: UUID | None = None
    thread_id: UUID
    message_id: UUID
    customer_id: UUID | None = None
    output: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    knowledge_hits: list[dict[str, Any]] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class InternalEmailReplyAutoSendCheckResponse(BaseModel):
    route: str
    auto_send_allowed: bool
    manual_review_required: bool
    manual_review_reason: str | None = None
    reasons: list[str] = Field(default_factory=list)
    block_reasons: list[dict[str, Any]] = Field(default_factory=list)
    dry_run: bool = True
    send_triggered: bool = False
    decision_json: dict[str, Any] = Field(default_factory=dict)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def require_agents_api_key(
    agents_api_key: str | None = Header(default=None, alias=AGENTS_API_KEY_HEADER),
) -> None:
    expected = settings.agents_api_key.get_secret_value().strip() if settings.agents_api_key else ""
    if not expected or not agents_api_key or not compare_digest(agents_api_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AGENTS_API_KEY_ERROR)


@router.post("/context", dependencies=[Depends(require_agents_api_key)])
async def load_email_reply_context(
    request: InternalEmailReplyContextRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> dict:
    def run(sync_session):
        statement = (
            select(EmailMessage)
            .options(
                selectinload(EmailMessage.thread),
                selectinload(EmailMessage.customer).selectinload(Customer.sources),
                selectinload(EmailMessage.customer).selectinload(Customer.outreach_records),
                selectinload(EmailMessage.customer).selectinload(Customer.vehicle_intents),
            )
            .where(EmailMessage.id == request.message_id)
        )
        message = sync_session.scalar(statement)
        if message is None:
            raise HTTPException(status_code=404, detail="email message 不存在。")
        customer = message.customer
        if request.customer_id is not None and customer is not None and customer.id != request.customer_id:
            raise HTTPException(status_code=400, detail="customer_id 与 message.customer_id 不一致。")
        return EmailReplyContextBuilder.build(
            customer=customer,
            message=message,
            knowledge_hits=[],
            risk_decision=None,
        )

    return await async_session.run_sync(run)


@router.post("/knowledge", response_model=KnowledgeRetrievalFilterResponse, dependencies=[Depends(require_agents_api_key)])
async def retrieve_email_reply_knowledge(
    request: KnowledgeRetrievalFilterRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeRetrievalFilterResponse:
    def run(sync_session):
        service = KnowledgeSearchService(sync_session)
        results, rejection_reason = service.retrieve_for_email_reply(**request.model_dump())
        return KnowledgeRetrievalFilterResponse(
            items=[serialize_retrieval_filter_result(result) for result in results],
            total=len(results),
            rejection_reason=rejection_reason,
        )

    return await async_session.run_sync(run)


@router.post(
    "/auto-send-check",
    response_model=InternalEmailReplyAutoSendCheckResponse,
    dependencies=[Depends(require_agents_api_key)],
)
async def check_email_reply_auto_send(
    request: InternalEmailReplyAutoSendCheckRequest,
) -> InternalEmailReplyAutoSendCheckResponse:
    context = request.context or {}
    customer = context.get("customer") if isinstance(context, dict) else {}
    customer = customer if isinstance(customer, dict) else {}
    inbound = context.get("inbound_message") if isinstance(context, dict) else {}
    inbound = inbound if isinstance(inbound, dict) else {}
    options = request.options or {}
    first_hit = request.knowledge_hits[0] if request.knowledge_hits else {}

    hard_block_decision = EmailReplyHardBlockService.evaluate(
        EmailReplyHardBlockInput(
            customer_do_not_contact=bool(customer.get("do_not_contact") or customer.get("do_not_contact_enabled")),
            customer_grade=customer.get("grade"),
            customer_status=customer.get("status"),
            inbound_risk_flags=list(inbound.get("risk_flags") or request.output.get("risk_flags") or []),
            sensitive_topics=list(inbound.get("sensitive_topics") or options.get("sensitive_topics") or []),
            reply_language_confident=bool(options.get("reply_language_confident", True)),
            has_same_language_knowledge=bool(request.knowledge_hits),
            has_cited_knowledge_evidence=any(hit.get("evidence_note") for hit in request.knowledge_hits),
            knowledge_retrieval_confident=bool(request.knowledge_hits) and not bool(context.get("knowledge_rejection_reason")),
            channel_risk_level=options.get("channel_risk_level"),
        )
    )
    eligibility_decision = EmailReplyAutoSendEligibilityService.evaluate(
        EmailReplyAutoSendEligibilityInput(
            customer_is_whitelisted=bool(customer.get("is_whitelisted") or options.get("customer_is_whitelisted")),
            knowledge_content_type=first_hit.get("content_type") or options.get("knowledge_content_type"),
            business_scene=first_hit.get("business_scene") or options.get("business_scene"),
            scene_risk_level=first_hit.get("risk_level") or options.get("scene_risk_level"),
            is_first_touch=bool(options.get("is_first_touch")),
            knowledge_auto_reply_allowed=bool(first_hit.get("auto_reply_allowed") or options.get("knowledge_auto_reply_allowed")),
            knowledge_embedding_ready=_is_embedding_ready(first_hit.get("embedding_status") or options.get("embedding_status")),
            reply_language_confident=bool(options.get("reply_language_confident", True)),
        )
    )
    decision_json = EmailReplyHardBlockService.enforce_priority(hard_block_decision, eligibility_decision)
    raw_route = str(decision_json.get("route") or "hold_for_manual_review")
    route = "block" if raw_route == "blocked" else raw_route
    if route == "auto_send_candidate":
        route = "auto_send"
    return InternalEmailReplyAutoSendCheckResponse(
        route=route,
        auto_send_allowed=bool(decision_json.get("auto_send_allowed", False)),
        manual_review_required=bool(decision_json.get("manual_review_required", True)),
        manual_review_reason=decision_json.get("manual_review_reason"),
        reasons=list(decision_json.get("reasons") or decision_json.get("auto_send_decision", {}).get("reasons") or []),
        block_reasons=list(decision_json.get("block_reasons") or []),
        dry_run=request.dry_run,
        send_triggered=False,
        decision_json=decision_json,
    )


def _is_embedding_ready(value: Any) -> bool:
    return str(value or "").strip().lower() in {"ready", "embedding_ready"}
