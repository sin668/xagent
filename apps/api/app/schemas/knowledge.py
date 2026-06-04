from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeCollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    status: str = Field(default="draft", pattern="^(draft|active|deprecated|disabled)$")
    review_status: str = Field(default="pending", pattern="^(pending|approved|rejected)$")
    version: str = "v1"
    source_ref: str | None = None


class KnowledgeCollectionResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    status: str
    review_status: str
    version: str
    source_ref: str | None
    created_at: str
    updated_at: str


class KnowledgeCollectionListResponse(BaseModel):
    items: list[KnowledgeCollectionResponse]


class KnowledgeItemCreate(BaseModel):
    collection_id: UUID
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    language: str = "zh"
    country: str | None = None
    applicable_channels: list = Field(default_factory=list)
    status: str = Field(default="draft", pattern="^(draft|active|deprecated|disabled)$")
    review_status: str = Field(default="pending", pattern="^(pending|approved|rejected)$")
    source_ref: str | None = None
    version: str = "v1"
    metadata_json: dict | None = None


class KnowledgeItemResponse(BaseModel):
    id: UUID
    collection_id: UUID
    title: str
    body: str
    language: str
    country: str | None
    applicable_channels: list
    status: str
    review_status: str
    source_ref: str | None
    version: str
    metadata_json: dict | None
    rag_eligible: bool
    created_at: str
    updated_at: str


class KnowledgeItemListResponse(BaseModel):
    items: list[KnowledgeItemResponse]


class KnowledgeEmbeddingCreate(BaseModel):
    embedding_model: str = Field(min_length=1, max_length=120)
    embedding: list[float] | None = None
    embedding_dimensions: int = 1536
    error_message: str | None = None


class KnowledgeEmbeddingResponse(BaseModel):
    id: UUID
    item_id: UUID
    embedding_model: str
    embedding_dimensions: int
    embedding_status: str
    error_message: str | None
    created_at: str


class PhaseOneKnowledgeImportRequest(BaseModel):
    dry_run: bool = False


class PhaseOneKnowledgeImportResponse(BaseModel):
    imported_count: int
    skipped_count: int
    collection_names: list[str]
    item_titles: list[str]


class KnowledgeSearchRequest(BaseModel):
    collection: str | None = None
    country: str | None = None
    language: str | None = None
    channel: str | None = None
    query: str | None = None
    query_embedding: list[float] | None = None
    allow_keyword_fallback: bool = True
    limit: int = Field(default=10, ge=1, le=50)


class KnowledgeSearchResultResponse(BaseModel):
    item: KnowledgeItemResponse
    score: float
    match_reason: str
    search_mode: str


class KnowledgeSearchResponse(BaseModel):
    items: list[KnowledgeSearchResultResponse]
    search_mode: str
    fallback_reason: str | None = None
