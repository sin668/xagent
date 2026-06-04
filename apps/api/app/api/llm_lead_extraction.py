from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.staging_leads import serialize_staging_lead
from app.db.session import AsyncSessionLocal
from app.schemas.llm_lead_extraction import LLMLeadExtractionRunRequest, LLMLeadExtractionRunResponse
from app.services.llm_lead_extraction import LLMLeadExtractionService

router = APIRouter(prefix="/llm-lead-extraction", tags=["llm-lead-extraction"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/run", response_model=LLMLeadExtractionRunResponse)
async def run_llm_lead_extraction(
    request: LLMLeadExtractionRunRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> LLMLeadExtractionRunResponse:
    def run(sync_session):
        service = LLMLeadExtractionService(sync_session)
        try:
            result = service.run_extraction(
                candidate_url_id=request.candidate_url_id,
                llm_output_json=request.llm_output_json,
            )
        except ValueError as exc:
            sync_session.commit()
            message = str(exc)
            status_code = 404 if "不存在" in message else 422
            raise HTTPException(status_code=status_code, detail=message) from exc
        sync_session.commit()
        return LLMLeadExtractionRunResponse(staging_lead=serialize_staging_lead(result.staging_lead))

    return await async_session.run_sync(run)

