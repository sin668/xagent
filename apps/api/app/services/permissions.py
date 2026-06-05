from enum import StrEnum

from app.models.enums import LeadCleanupSuggestionType


class Phase3Action(StrEnum):
    RESTORE_INVALID_OR_WATCH = "restore_invalid_or_watch"
    CANCEL_DO_NOT_CONTACT = "cancel_do_not_contact"
    DUPLICATE_OR_CUSTOMER_LEVEL_MERGE = "duplicate_or_customer_level_merge"
    C_GRADE_QUOTE_OR_CONTRACT = "c_grade_quote_or_contract"


class Phase3PermissionService:
    COMPLIANCE_OR_ADMIN_ROLES = {"compliance", "admin"}
    ADMIN_ONLY_ROLES = {"admin"}
    SALES_OR_CS_ROLES = {"sales", "customer_service", "customer-service", "cs", "客服", "销售"}
    ADMIN_ONLY_CLEANUP_TYPES = {
        LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        LeadCleanupSuggestionType.MERGE_CONTACT_METHOD,
        LeadCleanupSuggestionType.MERGE_SOURCE_EVIDENCE,
    }
    ADMIN_ONLY_CLEANUP_EXECUTION_TYPES = {
        LeadCleanupSuggestionType.STRONG_DUPLICATE,
        LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        LeadCleanupSuggestionType.MERGE_CONTACT_METHOD,
        LeadCleanupSuggestionType.MERGE_SOURCE_EVIDENCE,
    }

    @staticmethod
    def normalize_role(actor_role: str | None) -> str:
        return str(actor_role or "").strip().lower()

    @classmethod
    def ensure_allowed(cls, action: Phase3Action, *, actor_role: str | None) -> None:
        role = cls.normalize_role(actor_role)
        if action == Phase3Action.RESTORE_INVALID_OR_WATCH and role not in cls.COMPLIANCE_OR_ADMIN_ROLES:
            raise PermissionError("恢复 Invalid/Watch 仅允许合规或管理员。")
        if action == Phase3Action.CANCEL_DO_NOT_CONTACT and role not in cls.COMPLIANCE_OR_ADMIN_ROLES:
            raise PermissionError("取消勿扰仅允许合规或管理员。")
        if action == Phase3Action.DUPLICATE_OR_CUSTOMER_LEVEL_MERGE and role not in cls.ADMIN_ONLY_ROLES:
            raise PermissionError("疑似重复和客户级归并仅允许管理员。")

    @classmethod
    def ensure_cleanup_review_allowed(
        cls,
        suggestion_type: LeadCleanupSuggestionType,
        *,
        actor_role: str | None,
    ) -> None:
        if suggestion_type == LeadCleanupSuggestionType.RESTORE_FROM_WATCH:
            cls.ensure_allowed(Phase3Action.RESTORE_INVALID_OR_WATCH, actor_role=actor_role)
        if suggestion_type in cls.ADMIN_ONLY_CLEANUP_TYPES:
            cls.ensure_allowed(Phase3Action.DUPLICATE_OR_CUSTOMER_LEVEL_MERGE, actor_role=actor_role)

    @classmethod
    def ensure_cleanup_execution_allowed(
        cls,
        suggestion_type: LeadCleanupSuggestionType,
        *,
        actor_role: str | None,
    ) -> None:
        if suggestion_type in cls.ADMIN_ONLY_CLEANUP_EXECUTION_TYPES:
            role = cls.normalize_role(actor_role)
            if role not in cls.ADMIN_ONLY_ROLES:
                raise PermissionError("重复线索和客户级归并执行仅允许管理员。")
        if suggestion_type == LeadCleanupSuggestionType.RESTORE_FROM_WATCH:
            cls.ensure_allowed(Phase3Action.RESTORE_INVALID_OR_WATCH, actor_role=actor_role)

    @classmethod
    def ensure_c_grade_compliance_ready(
        cls,
        *,
        actor_role: str | None,
        compliance_approved: bool,
    ) -> None:
        role = cls.normalize_role(actor_role)
        if role in cls.SALES_OR_CS_ROLES and not compliance_approved:
            raise PermissionError("客服/销售不能绕过 C 级合规复核。")
