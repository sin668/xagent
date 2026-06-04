from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.staging_leads import serialize_staging_lead
from app.db.session import AsyncSessionLocal
from app.schemas.llm_lead_grading import LLMLeadGradingRunRequest, LLMLeadGradingRunResponse
from app.services.llm_lead_grading import LLMLeadGradingService

router = APIRouter(prefix="/llm-lead-grading", tags=["llm-lead-grading"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/run", response_model=LLMLeadGradingRunResponse)
async def run_llm_lead_grading(
    request: LLMLeadGradingRunRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> LLMLeadGradingRunResponse:
    def run(sync_session):
        service = LLMLeadGradingService(sync_session)
        try:
            result = service.run_grading(
                staging_lead_id=request.staging_lead_id,
                llm_output_json=request.llm_output_json,
                do_not_contact=request.do_not_contact,
            )
        except ValueError as exc:
            sync_session.commit()
            message = str(exc)
            status_code = 404 if "不存在" in message else 422
            raise HTTPException(status_code=status_code, detail=message) from exc
        sync_session.commit()
        return LLMLeadGradingRunResponse(
            staging_lead=serialize_staging_lead(result.staging_lead),
            rule_validation_result=service.rule_result_to_dict(result.rule_result),
        )

    return await async_session.run_sync(run)

