from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.adapters.email_reply_api import EmailReplyApiClient
from app.schemas.email_reply import EMAIL_REPLY_SCHEMA_VERSION, EmailReplyAgentOutput, EmailReplyKnowledgeHit, EmailReplyRequestEnvelope
from app.settings import get_settings


EMAIL_REPLY_NODE_SEQUENCE = ("load_context", "retrieve_knowledge")


@dataclass(slots=True)
class EmailReplyGraphState:
    request_id: UUID
    thread_id: UUID
    message_id: UUID
    customer_id: UUID | None = None
    draft_id: UUID | None = None
    context: dict[str, Any] = field(default_factory=dict)
    prompt: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    knowledge_hits: list[EmailReplyKnowledgeHit] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EmailReplyGraphResult:
    output: EmailReplyAgentOutput
    executed_nodes: list[str]


class EmailReplyGraphRunner:
    def __init__(self, *, api_client: EmailReplyApiClient | None = None) -> None:
        settings = get_settings()
        self.api_client = api_client or EmailReplyApiClient(
            base_url=self._api_base_url_from_options(settings),
            api_key=settings.agents_api_key,
        )
        self.executed_nodes: list[str] = []
        self.compiled_graph = self._build_graph()

    @staticmethod
    def _api_base_url_from_options(settings) -> str:
        return getattr(settings, "api_base_url", None) or "http://localhost:8000"

    def _build_graph(self):
        graph = StateGraph(EmailReplyGraphState)
        for node_name in EMAIL_REPLY_NODE_SEQUENCE:
            graph.add_node(node_name, getattr(self, node_name))
        graph.set_entry_point(EMAIL_REPLY_NODE_SEQUENCE[0])
        graph.add_edge("load_context", "retrieve_knowledge")
        graph.add_edge("retrieve_knowledge", END)
        return graph.compile()

    def mark(self, node_name: str) -> None:
        self.executed_nodes.append(node_name)

    def load_context(self, state: EmailReplyGraphState) -> EmailReplyGraphState:
        self.mark("load_context")
        envelope = EmailReplyRequestEnvelope(
            schema_version=EMAIL_REPLY_SCHEMA_VERSION,
            request_id=state.request_id,
            draft_id=state.draft_id,
            thread_id=state.thread_id,
            message_id=state.message_id,
            customer_id=state.customer_id,
            context=state.context,
            prompt=state.prompt,
            options=state.options,
        )
        state.context = self.api_client.load_context(envelope)
        state.audit["context_loaded"] = True
        state.audit["context_source"] = "apps_api_internal_http"
        return state

    def retrieve_knowledge(self, state: EmailReplyGraphState) -> EmailReplyGraphState:
        self.mark("retrieve_knowledge")
        options = state.options or {}
        inbound = state.context.get("inbound_message") if isinstance(state.context, dict) else {}
        inbound = inbound if isinstance(inbound, dict) else {}
        language = str(options.get("language") or inbound.get("language") or "Unknown")
        query = options.get("query")
        if query is None:
            query = inbound.get("body_text")
        response = self.api_client.retrieve_knowledge(
            query=query,
            language=language,
            channel=options.get("channel"),
            content_types=list(options.get("content_types") or ["qa_entry", "email_reply_template"]),
            business_scene=options.get("business_scene"),
            auto_send_candidate=bool(options.get("auto_send_candidate", False)),
            market=options.get("market"),
            tone=options.get("tone"),
            limit=int(options.get("limit") or 10),
        )
        state.knowledge_hits = [EmailReplyKnowledgeHit(**item) for item in response.get("items") or []]
        if response.get("rejection_reason"):
            state.risk_flags.append("knowledge_retrieval_rejected")
            state.audit["knowledge_rejection_reason"] = response.get("rejection_reason")
        state.audit["knowledge_retrieved"] = True
        state.audit["knowledge_hit_count"] = len(state.knowledge_hits)
        return state

    def run(self, state: EmailReplyGraphState) -> EmailReplyGraphResult:
        try:
            invoked_state = self.compiled_graph.invoke(state)
            state = self._state_from_graph_result(invoked_state)
        except Exception as exc:
            self._record_failure(exc)
            raise
        audit = {
            **state.audit,
            "writes_core_tables": False,
            "executed_nodes": list(self.executed_nodes),
        }
        output = EmailReplyAgentOutput(
            schema_version=EMAIL_REPLY_SCHEMA_VERSION,
            reply_language=str((state.options or {}).get("language") or (state.context.get("inbound_message") or {}).get("language") or "Unknown"),
            detected_language=(state.context.get("inbound_message") or {}).get("language") if isinstance(state.context, dict) else None,
            suggested_subject="Unknown",
            suggested_body="Unknown",
            knowledge_hits=state.knowledge_hits,
            risk_flags=state.risk_flags,
            auto_send_allowed=False,
            manual_review_required=True,
            next_action="hold_for_manual_review",
            audit=audit,
        )
        return EmailReplyGraphResult(output=output, executed_nodes=list(self.executed_nodes))

    def _record_failure(self, exc: Exception) -> None:
        self.last_error = {
            "error_type": "internal_api_error",
            "message": str(exc),
            "failed_node": self.executed_nodes[-1] if self.executed_nodes else None,
        }

    def _state_from_graph_result(self, result: EmailReplyGraphState | dict[str, Any]) -> EmailReplyGraphState:
        if isinstance(result, EmailReplyGraphState):
            return result
        return EmailReplyGraphState(
            request_id=result["request_id"],
            thread_id=result["thread_id"],
            message_id=result["message_id"],
            customer_id=result.get("customer_id"),
            draft_id=result.get("draft_id"),
            context=dict(result.get("context") or {}),
            prompt=dict(result.get("prompt") or {}),
            options=dict(result.get("options") or {}),
            knowledge_hits=[
                item if isinstance(item, EmailReplyKnowledgeHit) else EmailReplyKnowledgeHit(**item)
                for item in result.get("knowledge_hits") or []
            ],
            risk_flags=list(result.get("risk_flags") or []),
            audit=dict(result.get("audit") or {}),
        )
