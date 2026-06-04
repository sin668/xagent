from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.channel_risk import (
    ChannelRiskDecisionResponse,
    ChannelRiskEvaluateRequest,
    ChannelRiskRuleListResponse,
    ChannelRiskRuleResponse,
    ChannelRiskRuleUpsert,
)
from app.services.channel_risk import ChannelRiskService

router = APIRouter(prefix="/channel-risks", tags=["channel-risks"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_rule(rule) -> ChannelRiskRuleResponse:
    return ChannelRiskRuleResponse(
        channel_name=rule.channel_name,
        channel_type=rule.channel_type,
        risk_level=rule.risk_level.value,
        collection_allowed=rule.collection_allowed,
        ai_processing_allowed=rule.ai_processing_allowed,
        allowed_actions=rule.allowed_actions,
        forbidden_actions=rule.forbidden_actions,
        policy_source_url=rule.policy_source_url,
        notes=rule.notes,
        updated_by=rule.updated_by,
        updated_at=rule.updated_at.isoformat(),
    )


@router.get("", response_model=ChannelRiskRuleListResponse)
async def list_channel_risk_rules(async_session: AsyncSession = Depends(get_async_session)) -> ChannelRiskRuleListResponse:
    def run(sync_session):
        service = ChannelRiskService(sync_session)
        return ChannelRiskRuleListResponse(items=[serialize_rule(rule) for rule in service.list_rules()])

    return await async_session.run_sync(run)


@router.put("/{channel_name}", response_model=ChannelRiskRuleResponse)
async def upsert_channel_risk_rule(
    channel_name: str,
    request: ChannelRiskRuleUpsert,
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelRiskRuleResponse:
    def run(sync_session):
        service = ChannelRiskService(sync_session)
        rule = service.upsert_rule(
            channel_name=channel_name,
            channel_type=request.channel_type,
            risk_level=request.risk_level,
            allowed_actions=request.allowed_actions,
            forbidden_actions=request.forbidden_actions,
            policy_source_url=str(request.policy_source_url) if request.policy_source_url else None,
            notes=request.notes,
            external_id=request.external_id,
            collection_allowed=request.collection_allowed,
            updated_by=request.updated_by,
        )
        sync_session.commit()
        return serialize_rule(rule)

    return await async_session.run_sync(run)


@router.post("/evaluate-ai-task", response_model=ChannelRiskDecisionResponse)
async def evaluate_ai_task(
    request: ChannelRiskEvaluateRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelRiskDecisionResponse:
    def run(sync_session):
        service = ChannelRiskService(sync_session)
        decision = service.evaluate_ai_task(
            channel_name=request.channel_name,
            task_type=request.task_type,
            requested_action=request.requested_action,
            source_usage_type=request.source_usage_type,
            source_url=request.source_url,
            model_name=request.model_name,
            prompt_version=request.prompt_version,
        )
        sync_session.commit()
        return ChannelRiskDecisionResponse(
            allowed=decision.allowed,
            channel_name=decision.channel_name,
            risk_level=decision.risk_level,
            block_reason=decision.block_reason,
            audit_logged=decision.audit_logged,
        )

    return await async_session.run_sync(run)
