from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from app.adapters.email_reply_api import EmailReplyApiClient
from app.schemas.email_reply import EMAIL_REPLY_SCHEMA_VERSION, EmailReplyAgentOutput, EmailReplyKnowledgeHit, EmailReplyRequestEnvelope
from app.services.llm_client import LLMClient, LLMClientResult
from app.settings import get_settings


EMAIL_REPLY_NODE_SEQUENCE = (
    "load_context",
    "retrieve_knowledge",
    "draft_reply",
    "schema_validation",
    "auto_send_check",
    "route_decision",
)


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
    raw_draft: dict[str, Any] = field(default_factory=dict)
    validated_output: EmailReplyAgentOutput | None = None
    auto_send_decision: dict[str, Any] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EmailReplyGraphResult:
    output: EmailReplyAgentOutput
    executed_nodes: list[str]


class NullEmailReplyDrafter:
    def draft(self, *, context: dict, knowledge_hits: list[EmailReplyKnowledgeHit], prompt: dict, options: dict) -> dict:
        return {
            "schema_version": EMAIL_REPLY_SCHEMA_VERSION,
            "reply_language": str(options.get("language") or "Unknown"),
            "suggested_subject": "Unknown",
            "suggested_body": "Unknown",
            "auto_send_allowed": False,
            "manual_review_required": True,
            "next_action": "hold_for_manual_review",
            "audit": {"writes_core_tables": False},
        }


class LLMEmailReplyDrafter:
    task_type = "EMAIL_REPLY"

    def __init__(self, *, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def draft(self, *, context: dict, knowledge_hits: list[EmailReplyKnowledgeHit], prompt: dict, options: dict) -> dict:
        result = self.llm_client.generate_json(
            task_type=self.task_type,
            system_prompt=self._system_prompt(prompt),
            user_prompt=self._user_prompt(context=context, knowledge_hits=knowledge_hits, prompt=prompt, options=options),
            output_schema=EmailReplyAgentOutput.model_json_schema(),
        )
        if result.error or not isinstance(result.output_json, dict):
            return self._manual_review_fallback(result=result, options=options)
        return self._with_audit(result.output_json, result)

    @staticmethod
    def _system_prompt(prompt: dict) -> str:
        configured = prompt.get("system_prompt") or prompt.get("system")
        if configured:
            return str(configured)
        return (
            "你是海外车辆采购邮件回复 Agent。只能基于客户上下文和已审核知识生成结构化 JSON，"
            "不得编造事实，不得承诺价格、合同、税务、法律、交付或出口管制事项。"
            "缺失字段输出 Unknown、null 或空数组。不得写入业务 core 表。"
        )

    @staticmethod
    def _user_prompt(
        *,
        context: dict,
        knowledge_hits: list[EmailReplyKnowledgeHit],
        prompt: dict,
        options: dict,
    ) -> str:
        payload = {
            "context": context,
            "knowledge_hits": [item.model_dump(mode="json") for item in knowledge_hits],
            "prompt": prompt,
            "options": options,
            "requirements": [
                "输出 schema_version=email-reply-v1。",
                "audit.writes_core_tables 必须为 false。",
                "知识证据不足、语言不确定、DNC/D/E 或敏感承诺场景必须 manual_review_required=true。",
                "auto_send_allowed 只能作为候选建议，最终发送必须由 apps/api 决策。",
            ],
        }
        import json

        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _with_audit(output_json: dict, result: LLMClientResult) -> dict:
        output = dict(output_json)
        audit = dict(output.get("audit") or {})
        audit.update(
            {
                "writes_core_tables": False,
                "llm_provider": result.provider,
                "llm_model": result.model,
                "llm_base_url": result.base_url,
                "latency_ms": result.latency_ms,
                "token_usage": result.token_usage,
            }
        )
        output["audit"] = audit
        return output

    @staticmethod
    def _manual_review_fallback(*, result: LLMClientResult, options: dict) -> dict:
        return {
            "schema_version": EMAIL_REPLY_SCHEMA_VERSION,
            "reply_language": str(options.get("language") or "Unknown"),
            "detected_language": None,
            "suggested_subject": "Unknown",
            "suggested_body": "Unknown",
            "knowledge_hits": [],
            "risk_flags": ["llm_unavailable"],
            "auto_send_allowed": False,
            "manual_review_required": True,
            "next_action": "hold_for_manual_review",
            "audit": {
                "writes_core_tables": False,
                "llm_provider": result.provider,
                "llm_model": result.model,
                "llm_base_url": result.base_url,
                "latency_ms": result.latency_ms,
                "token_usage": result.token_usage,
                "llm_error": result.error or {"type": "parse_error", "message": "LLM output is not a JSON object."},
            },
        }


class EmailReplyGraphRunner:
    def __init__(self, *, api_client: EmailReplyApiClient | None = None, llm_drafter=None) -> None:
        settings = get_settings()
        self.api_client = api_client or EmailReplyApiClient(
            base_url=self._api_base_url_from_options(settings),
            api_key=settings.agents_api_key,
        )
        self.llm_drafter = llm_drafter or LLMEmailReplyDrafter()
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
        for index, node_name in enumerate(EMAIL_REPLY_NODE_SEQUENCE):
            next_index = index + 1
            graph.add_edge(
                node_name,
                EMAIL_REPLY_NODE_SEQUENCE[next_index] if next_index < len(EMAIL_REPLY_NODE_SEQUENCE) else END,
            )
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

    def draft_reply(self, state: EmailReplyGraphState) -> EmailReplyGraphState:
        self.mark("draft_reply")
        state.raw_draft = dict(
            self.llm_drafter.draft(
                context=state.context,
                knowledge_hits=state.knowledge_hits,
                prompt=state.prompt,
                options=state.options,
            )
            or {}
        )
        state.audit["draft_reply_generated"] = True
        return state

    def schema_validation(self, state: EmailReplyGraphState) -> EmailReplyGraphState:
        self.mark("schema_validation")
        normalized = self._normalize_draft_output(state)
        try:
            state.validated_output = EmailReplyAgentOutput(**normalized)
        except ValidationError as exc:
            trace = {
                "node": "schema_validation",
                "status": "failed",
                "error": {
                    "error_type": "schema_validation_error",
                    "message": str(exc),
                    "retryable": False,
                },
            }
            self.last_error = {
                "error_type": "schema_validation_error",
                "message": str(exc),
                "failed_node": "schema_validation",
                "trace": trace,
            }
            raise ValueError(f"schema_validation failed: {exc}") from exc
        state.audit["schema_validation_status"] = "succeeded"
        return state

    def auto_send_check(self, state: EmailReplyGraphState) -> EmailReplyGraphState:
        self.mark("auto_send_check")
        if state.validated_output is None:
            raise ValueError("auto_send_check requires validated_output.")
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
        state.auto_send_decision = self.api_client.auto_send_check(
            envelope=envelope,
            output=state.validated_output.model_dump(mode="json"),
            context=state.context,
            knowledge_hits=[
                item.model_dump(mode="json") if isinstance(item, EmailReplyKnowledgeHit) else dict(item)
                for item in state.knowledge_hits
            ],
            options=state.options,
            dry_run=bool((state.options or {}).get("dry_run", True)),
        )
        state.audit["auto_send_check_completed"] = True
        return state

    def route_decision(self, state: EmailReplyGraphState) -> EmailReplyGraphState:
        self.mark("route_decision")
        if state.validated_output is None:
            raise ValueError("route_decision requires validated_output.")
        decision = dict(state.auto_send_decision or {})
        route = str(decision.get("route") or "hold_for_manual_review")
        normalized_route = "block" if route == "blocked" else route
        if normalized_route == "auto_send":
            next_action = "auto_send_candidate"
        elif normalized_route == "block":
            next_action = "block"
        else:
            next_action = "hold_for_manual_review"

        update_payload = {
            **state.validated_output.model_dump(),
            "auto_send_allowed": bool(decision.get("auto_send_allowed", False)),
            "manual_review_required": bool(decision.get("manual_review_required", True)),
            "next_action": next_action,
        }
        state.validated_output = EmailReplyAgentOutput(**update_payload)
        state.audit["route_decision"] = normalized_route
        state.audit["route_reasons"] = list(decision.get("reasons") or [])
        state.audit["manual_review_reason"] = decision.get("manual_review_reason")
        state.audit["block_reasons"] = list(decision.get("block_reasons") or [])
        state.audit["dry_run"] = bool(decision.get("dry_run", True))
        state.audit["send_triggered"] = bool(decision.get("send_triggered", False))
        return state

    def run(self, state: EmailReplyGraphState) -> EmailReplyGraphResult:
        try:
            invoked_state = self.compiled_graph.invoke(state)
            state = self._state_from_graph_result(invoked_state)
        except Exception as exc:
            if not getattr(self, "last_error", None):
                self._record_failure(exc)
            raise
        audit = {
            **state.audit,
            "writes_core_tables": False,
            "executed_nodes": list(self.executed_nodes),
        }
        output = state.validated_output or EmailReplyAgentOutput(**self._normalize_draft_output(state))
        output.audit.update(audit)
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
            raw_draft=dict(result.get("raw_draft") or {}),
            validated_output=result.get("validated_output"),
            auto_send_decision=dict(result.get("auto_send_decision") or {}),
            risk_flags=list(result.get("risk_flags") or []),
            audit=dict(result.get("audit") or {}),
        )

    def _normalize_draft_output(self, state: EmailReplyGraphState) -> dict[str, Any]:
        raw = dict(state.raw_draft or {})
        missing_required: list[str] = []
        inbound = state.context.get("inbound_message") if isinstance(state.context, dict) else {}
        inbound = inbound if isinstance(inbound, dict) else {}
        knowledge_hits = list(raw.get("knowledge_hits") or state.knowledge_hits or [])
        risk_flags = list(raw.get("risk_flags") or [])

        def get_or_unknown(key: str) -> str:
            value = raw.get(key)
            if value is None or str(value).strip() == "":
                missing_required.append(key)
                return "Unknown"
            return str(value)

        reply_language = get_or_unknown("reply_language")
        suggested_subject = get_or_unknown("suggested_subject")
        suggested_body = get_or_unknown("suggested_body")
        auto_send_allowed = bool(raw.get("auto_send_allowed", False))
        manual_review_required = bool(raw.get("manual_review_required", True))
        next_action = raw.get("next_action") or "hold_for_manual_review"

        if missing_required:
            risk_flags.append("llm_missing_required_fields")
            auto_send_allowed = False
            manual_review_required = True
            next_action = "hold_for_manual_review"
        if not knowledge_hits:
            risk_flags.append("knowledge_hits_insufficient")
            auto_send_allowed = False
            manual_review_required = True
            next_action = "hold_for_manual_review"

        audit = dict(raw.get("audit") or {})
        audit.setdefault("writes_core_tables", False)
        audit.update(state.audit)
        audit["knowledge_hit_count"] = len(knowledge_hits)

        return {
            "schema_version": raw.get("schema_version") or EMAIL_REPLY_SCHEMA_VERSION,
            "reply_language": reply_language,
            "detected_language": raw.get("detected_language") or inbound.get("language"),
            "suggested_subject": suggested_subject,
            "suggested_body": suggested_body,
            "knowledge_hits": knowledge_hits,
            "risk_flags": sorted(set([*state.risk_flags, *risk_flags])),
            "auto_send_allowed": auto_send_allowed,
            "manual_review_required": manual_review_required,
            "next_action": next_action,
            "audit": audit,
        }
