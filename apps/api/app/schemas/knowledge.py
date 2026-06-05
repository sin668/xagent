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
    content_type: str | None = Field(
        default=None,
        pattern="^(qa_entry|email_reply_template|compliance_phrase|vehicle_product_note|process_sop)$",
    )
    business_scene: str | None = None
    risk_level: str | None = None
    auto_reply_allowed: bool | None = None
    market: str | None = None
    tone: str | None = None


class KnowledgeItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    language: str | None = None
    country: str | None = None
    applicable_channels: list | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|deprecated|disabled)$")
    review_status: str | None = Field(default=None, pattern="^(pending|approved|rejected)$")
    source_ref: str | None = None
    version: str | None = None
    metadata_json: dict | None = None
    content_type: str | None = Field(
        default=None,
        pattern="^(qa_entry|email_reply_template|compliance_phrase|vehicle_product_note|process_sop)$",
    )
    business_scene: str | None = None
    risk_level: str | None = None
    auto_reply_allowed: bool | None = None
    market: str | None = None
    tone: str | None = None
    change_reason: str | None = None


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
    content_type: str | None = None
    business_scene: str | None = None
    risk_level: str | None = None
    auto_reply_allowed: bool | None = None
    market: str | None = None
    tone: str | None = None
    rag_eligible: bool
    created_at: str
    updated_at: str


class KnowledgeItemListResponse(BaseModel):
    items: list[KnowledgeItemResponse]


class KnowledgeReviewActionRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    actor_role: str = Field(min_length=1, max_length=80)
    review_note: str | None = None


class KnowledgeReviewLogResponse(BaseModel):
    id: UUID
    item_id: str | None
    action: str
    reviewer: str | None
    input_ref: str | None
    output_ref: str | None
    result: str
    error_message: str | None
    created_at: str


class KnowledgeReviewLogListResponse(BaseModel):
    items: list[KnowledgeReviewLogResponse]
    total: int


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
    content_type: str | None = Field(
        default=None,
        pattern="^(qa_entry|email_reply_template|compliance_phrase|vehicle_product_note|process_sop)$",
    )
    business_scene: str | None = None
    risk_level: str | None = None
    auto_reply_only: bool = False
    market: str | None = None
    tone: str | None = None
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


class KnowledgeRetrievalFilterRequest(BaseModel):
    query: str | None = None
    language: str = Field(min_length=1, max_length=20)
    channel: str | None = None
    content_types: list[str] = Field(default_factory=list)
    business_scene: str | None = None
    auto_send_candidate: bool = False
    market: str | None = None
    tone: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class KnowledgeRetrievalFilterResultResponse(BaseModel):
    knowledge_item_id: UUID
    version: str
    similarity_score: float
    title: str
    content_type: str | None = None
    business_scene: str | None = None
    filter_conditions: dict


class KnowledgeRetrievalFilterResponse(BaseModel):
    items: list[KnowledgeRetrievalFilterResultResponse]
    total: int
    rejection_reason: str | None = None


class KnowledgeRagRetrievalTestRequest(BaseModel):
    query: str | None = None
    language: str = Field(min_length=1, max_length=20)
    channel: str | None = None
    content_type: str | None = Field(
        default=None,
        pattern="^(qa_entry|email_reply_template|compliance_phrase|vehicle_product_note|process_sop)$",
    )
    content_types: list[str] | None = None
    business_scene: str | None = None
    auto_send_context: bool = False
    market: str | None = None
    tone: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class KnowledgeRagRetrievalTestResponse(BaseModel):
    dry_run: bool
    triggered_send: bool
    items: list[KnowledgeRetrievalFilterResultResponse]
    total: int
    filter_conditions: dict
    rejection_reason: str | None = None


class KnowledgeUsageRecordCreate(BaseModel):
    email_reply_draft_id: UUID | None = None
    retrieval_query: str | None = None
    similarity_score: float | None = None
    rank: int | None = None
    filters_json: dict = Field(default_factory=dict)
    outcome: str = Field(
        default="retrieved",
        pattern="^(retrieved|adopted|edited|rejected|customer_replied|bounced|suggest_deprecate)$",
    )
    adopted: bool = False
    edit_distance_ratio: float | None = None
    caused_bounce: bool = False
    customer_replied: bool = False
    suggest_deprecate: bool = False
    suggest_deprecate_reason: str | None = None


class KnowledgeUsageRecordResponse(BaseModel):
    id: UUID
    knowledge_item_id: UUID
    knowledge_version: str
    email_reply_draft_id: UUID | None = None
    retrieval_query: str | None = None
    similarity_score: float | None = None
    rank: int | None = None
    filters_json: dict
    outcome: str
    adopted: bool
    edit_distance_ratio: float | None = None
    caused_bounce: bool
    customer_replied: bool
    suggest_deprecate: bool
    suggest_deprecate_reason: str | None = None
    created_at: str


class KnowledgeQualitySummaryResponse(BaseModel):
    knowledge_item_id: UUID
    knowledge_version: str
    retrieval_count: int
    adoption_count: int
    adoption_rate: float
    average_edit_distance_ratio: float | None = None
    bounce_count: int
    bounce_rate: float
    customer_reply_count: int
    customer_reply_rate: float
    suggest_deprecate: bool
    suggest_deprecate_reason: str | None = None
