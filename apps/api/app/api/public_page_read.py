from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.raw_collection import serialize_snapshot
from app.db.session import AsyncSessionLocal
from app.schemas.public_page_read import PublicPageReadRunRequest, PublicPageReadRunResponse
from app.services.public_page_read_agent import PublicPageReadAgentService

router = APIRouter(prefix="/public-page-read", tags=["public-page-read"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/run", response_model=PublicPageReadRunResponse)
async def run_public_page_read(
    request: PublicPageReadRunRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> PublicPageReadRunResponse:
    def run(sync_session):
        service = PublicPageReadAgentService(sync_session)
        try:
            result = service.read_candidate_page(
                candidate_url_id=request.candidate_url_id,
                public_html=request.public_html,
            )
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if "不存在" in message else 422
            raise HTTPException(status_code=status_code, detail=message) from exc
        sync_session.commit()
        return PublicPageReadRunResponse(
            snapshot=serialize_snapshot(
                result.snapshot_result.page_snapshot,
                latest_for_candidate_id=result.snapshot_result.latest_for_candidate.id,
            )
        )

    return await async_session.run_sync(run)

