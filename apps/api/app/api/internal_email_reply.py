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
from app.services.email_reply_context import EmailReplyContextBuilder
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
