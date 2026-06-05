from enum import StrEnum


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class CustomerType(StrEnum):
    LOCAL_DEALER_SECONDARY_DEALER = "local_dealer_secondary_dealer"
    DEALERSHIP_DIRECTORY = "dealership_directory"
    MARKETPLACE = "marketplace"
    PERSONAL_BUYER = "personal_buyer"
    KOL_AUTO_BLOGGER = "kol_auto_blogger"
    UNKNOWN = "unknown"
    NON_TARGET = "non_target"


class CustomerGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    INVALID = "Invalid"
    WATCH = "Watch"


class CustomerStatus(StrEnum):
    NEW = "new"
    NEEDS_ENRICHMENT = "needs_enrichment"
    PENDING_REVIEW = "pending_review"
    READY_FOR_CUSTOMER_SERVICE = "ready_for_customer_service"
    CUSTOMER_SERVICE_FOLLOWING = "customer_service_following"
    READY_FOR_SALES = "ready_for_sales"
    SALES_FOLLOWING = "sales_following"
    QUOTED = "quoted"
    INVALID = "invalid"
    WATCH = "watch"
    DO_NOT_CONTACT = "do_not_contact"


class ContactMethodType(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    VKONTAKTE = "vkontakte"
    ODNOKLASSNIKI = "odnoklassniki"
    TIKTOK = "tiktok"
    MAX = "max"
    WEBSITE = "website"
    WEBSITE_FORM = "website_form"
    OTHER = "other"


class SourcePlatform(StrEnum):
    OFFICIAL_WEBSITE = "official_website"
    PUBLIC_DIRECTORY = "public_directory"
    SEARCH_ENGINE = "search_engine"
    GOOGLE_MAPS = "google_maps"
    YANDEX_MAPS = "yandex_maps"
    YOUTUBE = "youtube"
    DROM = "drom"
    OTHER = "other"


class ChannelRiskLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    FORBIDDEN = "Forbidden"


class SourceUsageType(StrEnum):
    AUTOMATIC_COLLECTION = "automatic_collection"
    PUBLIC_DISCOVERY_ONLY = "public_discovery_only"
    MANUAL_SAMPLE = "manual_sample"
    POLICY_RESEARCH = "policy_research"


class ChannelPlanStatus(StrEnum):
    DRAFT = "draft"
    ENABLED = "enabled"
    PAUSED = "paused"
    ARCHIVED = "archived"


class CollectionTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class CandidateUrlStatus(StrEnum):
    NEW = "new"
    STAGED = "staged"
    DUPLICATE = "duplicate"
    BLOCKED = "blocked"
    FAILED = "failed"


class PageSnapshotReadStatus(StrEnum):
    SUCCESS = "success"
    BLOCKED = "blocked"
    FAILED = "failed"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class StagingReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    NEEDS_SECONDARY_VERIFICATION = "needs_secondary_verification"
    APPROVED = "approved"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


class StagingQueueStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    BLOCKED = "blocked"


class RiskEventSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskEventStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class OutreachStatus(StrEnum):
    DRAFT = "draft"
    READY_FOR_MANUAL_SEND = "ready_for_manual_send"
    SENT = "sent"
    REPLIED = "replied"
    REJECTED = "rejected"
    NO_RESPONSE = "no_response"
    BAD_CONTACT = "bad_contact"
    CLOSED = "closed"


class EmailThreadStatus(StrEnum):
    OPEN = "open"
    WAITING_REPLY = "waiting_reply"
    REPLIED = "replied"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class EmailMessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class EmailMessageStatus(StrEnum):
    RECEIVED = "received"
    PENDING_REPLY = "pending_reply"
    DRAFTED = "drafted"
    SENT = "sent"
    FAILED = "failed"
    ARCHIVED = "archived"


class EmailMessageSourceType(StrEnum):
    MANUAL = "manual"
    API_IMPORT = "api_import"
    MAILBOX_SYNC = "mailbox_sync"


class AITaskType(StrEnum):
    LEAD_EXTRACTION = "lead_extraction"
    LEAD_GRADING = "lead_grading"
    OUTREACH_DRAFT = "outreach_draft"
    INVENTORY_MATCHING = "inventory_matching"
    RISK_BLOCK = "risk_block"


class ComplianceReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NOT_REQUIRED = "not_required"


class SyncStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ScriptReviewStatus(StrEnum):
    DRAFT = "draft"
    BUSINESS_REVIEW = "business_review"
    COMPLIANCE_REVIEW = "compliance_review"
    APPROVED_FOR_EXTERNAL_USE = "approved_for_external_use"
    DISABLED = "disabled"


class FailedCaseType(StrEnum):
    FETCH_FAILED = "fetch_failed"
    SCHEMA_INVALID = "schema_invalid"
    MISSING_EVIDENCE = "missing_evidence"
    RISK_BLOCKED = "risk_blocked"
    DUPLICATE = "duplicate"
    LLM_SUSPECTED_FABRICATION = "llm_suspected_fabrication"


class KnowledgeItemStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class KnowledgeReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class KnowledgeEmbeddingStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class LLMPromptTaskType(StrEnum):
    SOURCE_DISCOVERY = "SOURCE_DISCOVERY"
    LEAD_EXTRACTION = "LEAD_EXTRACTION"
    LEAD_GRADING = "LEAD_GRADING"
    EMAIL_REPLY_DRAFT = "EMAIL_REPLY_DRAFT"
    EMAIL_REPLY_AUTO_SEND_CHECK = "EMAIL_REPLY_AUTO_SEND_CHECK"
    EMAIL_REPLY_KNOWLEDGE_RETRIEVAL = "EMAIL_REPLY_KNOWLEDGE_RETRIEVAL"
    EMAIL_REPLY_SEND = "EMAIL_REPLY_SEND"


class LLMPromptTemplateStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class AgentTaskType(StrEnum):
    SOURCE_DISCOVERY = "SOURCE_DISCOVERY"
    LEAD_EXTRACTION = "LEAD_EXTRACTION"
    LEAD_GRADING = "LEAD_GRADING"
    RETRY_WORKER = "RETRY_WORKER"


class AgentTaskRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class LeadSourceCandidateReviewStatus(StrEnum):
    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    APPROVED = "approved"
    REJECTED = "rejected"
    HIGH_RISK_REVIEW = "high_risk_review"
    PAUSED = "paused"
    NEEDS_RECHECK = "needs_recheck"


class LeadSourceCandidateExtractionStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY = "retry"
    BLOCKED = "blocked"


class LeadEnrichmentType(StrEnum):
    AI_DEEP_RESEARCH = "ai_deep_research"
    MANUAL_SUPPLEMENT = "manual_supplement"


class LeadEnrichmentResultStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LeadEnrichmentFieldSourceType(StrEnum):
    AI_PUBLIC_SOURCE = "ai_public_source"
    MANUAL_PUBLIC_INFO = "manual_public_info"
    MANUAL_CUSTOMER_REPLY = "manual_customer_reply"
    MANUAL_BUSINESS_NOTE = "manual_business_note"
    UNKNOWN = "unknown"


class LeadEnrichmentFieldReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class LeadCleanupRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LeadCleanupSuggestionType(StrEnum):
    STRONG_DUPLICATE = "strong_duplicate"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    MERGE_CONTACT_METHOD = "merge_contact_method"
    MERGE_SOURCE_EVIDENCE = "merge_source_evidence"
    RESTORE_FROM_WATCH = "restore_from_watch"
    CONFIRM_INVALID = "confirm_invalid"
    MARK_ABANDONED = "mark_abandoned"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class LeadCleanupSuggestionReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class CustomerVehicleIntentSourceType(StrEnum):
    MANUAL_CUSTOMER_REPLY = "manual_customer_reply"
    MANUAL_BUSINESS_NOTE = "manual_business_note"
    AI_ENRICHMENT_ACCEPTED = "ai_enrichment_accepted"
    IMPORTED = "imported"
    UNKNOWN = "unknown"


class CustomerVehicleIntentStatus(StrEnum):
    ACTIVE = "active"
    PENDING_CONFIRMATION = "pending_confirmation"
    FULFILLED = "fulfilled"
    ARCHIVED = "archived"


class CustomerFollowupTeam(StrEnum):
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    EXPORT = "export"
    COMPLIANCE = "compliance"
    OPERATIONS = "operations"


class CustomerFollowupType(StrEnum):
    MANUAL_CALL = "manual_call"
    MANUAL_MESSAGE = "manual_message"
    EMAIL = "email"
    CUSTOMER_REPLY = "customer_reply"
    INTERNAL_NOTE = "internal_note"
    COMPLIANCE_REVIEW = "compliance_review"
