PHASE5_ROLLBACK_STRATEGY = (
    "第五阶段数据底座 migration 使用 Alembic downgrade 顺序回滚："
    "20260605_0035 -> 20260605_0034 -> 20260605_0033 -> 20260605_0032 -> 20260605_0031 -> 20260605_0030 -> 20260605_0029 -> 20260605_0028。"
    "回滚前必须确认新增表中没有需要保留的业务数据，或先完成数据备份和迁移归档。"
)


PHASE5_MIGRATION_CONTRACTS = [
    {
        "revision": "20260605_0029",
        "down_revision": "20260604_0028",
        "filename": "20260605_0029_extend_llm_prompt_templates_governance.py",
        "tables": {
            "llm_prompt_templates": [
                "source_file_path",
                "source_file_hash",
                "migration_batch_id",
                "parent_template_id",
                "published_by",
                "published_at",
                "change_summary",
                "rollback_from_template_id",
                "validation_status",
                "validation_errors_json",
            ]
        },
        "enums": {
            "llmprompttasktype": [
                "EMAIL_REPLY_DRAFT",
                "EMAIL_REPLY_AUTO_SEND_CHECK",
                "EMAIL_REPLY_KNOWLEDGE_RETRIEVAL",
                "EMAIL_REPLY_SEND",
            ]
        },
    },
    {
        "revision": "20260605_0030",
        "down_revision": "20260605_0029",
        "filename": "20260605_0030_create_email_threads_messages.py",
        "tables": {
            "email_threads": [
                "id",
                "customer_id",
                "subject",
                "status",
                "channel_account",
                "last_message_at",
                "created_at",
                "updated_at",
            ],
            "email_messages": [
                "id",
                "thread_id",
                "customer_id",
                "direction",
                "from_email",
                "to_emails",
                "cc_emails",
                "subject",
                "body_text",
                "body_html",
                "language",
                "status",
                "source_type",
                "external_message_id",
                "created_at",
                "updated_at",
            ],
        },
        "enums": {
            "emailthreadstatus": ["open", "waiting_reply", "replied", "archived", "blocked"],
            "emailmessagedirection": ["inbound", "outbound"],
            "emailmessagestatus": ["received", "pending_reply", "drafted", "sent", "failed", "archived"],
            "emailmessagesourcetype": ["manual", "api_import", "mailbox_sync"],
        },
    },
    {
        "revision": "20260605_0031",
        "down_revision": "20260605_0030",
        "filename": "20260605_0031_create_email_reply_drafts.py",
        "tables": {
            "email_reply_drafts": [
                "id",
                "thread_id",
                "message_id",
                "customer_id",
                "agent_service_run_id",
                "agent_task_run_id",
                "prompt_template_id",
                "prompt_version",
                "model",
                "ai_suggested_subject",
                "ai_suggested_body",
                "final_subject",
                "final_body",
                "knowledge_hits_json",
                "auto_send_allowed",
                "auto_send_decision_json",
                "manual_review_required",
                "status",
                "sent_record_id",
            ]
        },
        "enums": {
            "emailreplydraftstatus": [
                "drafted",
                "pending_review",
                "approved",
                "sent",
                "rejected",
                "blocked",
                "failed",
            ]
        },
    },
    {
        "revision": "20260605_0032",
        "down_revision": "20260605_0031",
        "filename": "20260605_0032_create_email_send_attempts.py",
        "tables": {
            "email_send_attempts": [
                "id",
                "reply_draft_id",
                "outreach_record_id",
                "provider",
                "provider_message_id",
                "from_email",
                "to_emails",
                "subject_snapshot",
                "body_text_snapshot",
                "status",
                "attempt_count",
                "error_message",
                "bounce_reason",
                "sent_at",
            ]
        },
        "enums": {
            "emailsendattemptstatus": [
                "pending",
                "sending",
                "sent",
                "failed",
                "retry_pending",
                "bounced",
                "blocked",
            ]
        },
    },
    {
        "revision": "20260605_0033",
        "down_revision": "20260605_0032",
        "filename": "20260605_0033_create_knowledge_usage_quality.py",
        "tables": {
            "knowledge_usage_records": [
                "id",
                "knowledge_item_id",
                "knowledge_version",
                "email_reply_draft_id",
                "retrieval_query",
                "similarity_score",
                "filters_json",
                "outcome",
                "adopted",
                "edit_distance_ratio",
                "caused_bounce",
                "customer_replied",
                "suggest_deprecate",
            ],
            "knowledge_quality_metrics": [
                "id",
                "knowledge_item_id",
                "knowledge_version",
                "period_start",
                "period_end",
                "retrieval_count",
                "adoption_rate",
                "average_edit_distance_ratio",
                "bounce_rate",
                "customer_reply_rate",
                "suggest_deprecate",
            ],
        },
        "enums": {
            "knowledgeusageoutcome": [
                "retrieved",
                "adopted",
                "edited",
                "rejected",
                "customer_replied",
                "bounced",
                "suggest_deprecate",
            ]
        },
    },
    {
        "revision": "20260605_0034",
        "down_revision": "20260605_0033",
        "filename": "20260605_0034_scope_llm_prompt_default_by_provider_model.py",
        "indexes": {
            "llm_prompt_templates": [
                "uq_llm_prompt_templates_active_default_scope",
            ]
        },
    },
    {
        "revision": "20260605_0035",
        "down_revision": "20260605_0034",
        "filename": "20260605_0035_add_knowledge_embedding_retry_metrics.py",
        "tables": {
            "knowledge_embeddings": [
                "last_error_message",
                "retry_count",
            ]
        },
        "indexes": {
            "knowledge_embeddings": [
                "ix_knowledge_embeddings_retry_count",
            ]
        },
    },
]
