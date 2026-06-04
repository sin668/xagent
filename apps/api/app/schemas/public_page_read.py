from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.raw_collection import PageSnapshotResponse


class PublicPageReadRunRequest(BaseModel):
    candidate_url_id: UUID
    public_html: str | None = Field(
        default=None,
        description="可选：人工或受控工具读取到的公开 HTML/文本；为空时由服务端执行单 URL 公开读取。",
    )


class PublicPageReadRunResponse(BaseModel):
    snapshot: PageSnapshotResponse

