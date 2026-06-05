from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, StateGraph

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.lead_extraction import LeadExtractionCandidate
from app.schemas.lead_grading import LeadGradingAgentOutput, LeadGradingSuggestion
from app.services.agent_logging import run_logged_node


LEAD_GRADING_NODE_SEQUENCE = (
    "load_extracted_lead",
    "score_lead_signals",
    "apply_hard_rules",
    "explain_grade_delta",
    "output_shadow_grading",
)


@dataclass(slots=True)
class LeadGradingGraphState:
    grading_run_id: str
    extracted_lead: LeadExtractionCandidate | dict[str, Any]
    agent_mode: str = "shadow"
    risk_flags: list[str] = field(default_factory=list)
    existing_grade: str | None = None
    signal_score: int = 0
    reasons: list[str] = field(default_factory=list)
    triggered_rules: list[str] = field(default_factory=list)
    recommended_grade: str | None = None
    status_route: str | None = None
    confidence_score: float = 0
    explanations: dict[str, str] = field(default_factory=dict)
    suggestion: LeadGradingSuggestion | None = None
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LeadGradingGraphResult:
    output: LeadGradingAgentOutput
    executed_nodes: list[str]


class LeadGradingGraphRunner:
    agent_type = "lead_grading"

    def __init__(self, *, boundary: ApiContractBoundary | None = None) -> None:
        self.boundary = boundary or ApiContractBoundary()
        self.executed_nodes: list[str] = []
        self.compiled_graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(LeadGradingGraphState)
        for node_name in LEAD_GRADING_NODE_SEQUENCE:
            graph.add_node(
                node_name,
                lambda state, node_name=node_name: run_logged_node(
                    agent_type=self.agent_type,
                    node_name=node_name,
                    func=getattr(self, node_name),
                    state=state,
                ),
            )
        graph.set_entry_point(LEAD_GRADING_NODE_SEQUENCE[0])
        for index, node_name in enumerate(LEAD_GRADING_NODE_SEQUENCE):
            next_index = index + 1
            graph.add_edge(
                node_name,
                LEAD_GRADING_NODE_SEQUENCE[next_index] if next_index < len(LEAD_GRADING_NODE_SEQUENCE) else END,
            )
        return graph.compile()

    def mark(self, node_name: str) -> None:
        self.executed_nodes.append(node_name)

    @staticmethod
    def set_node_summary(state: LeadGradingGraphState, node_name: str, summary: dict[str, Any]) -> None:
        state.audit.setdefault("node_summaries", {})[node_name] = summary

    def load_extracted_lead(self, state: LeadGradingGraphState) -> LeadGradingGraphState:
        self.mark("load_extracted_lead")
        if state.agent_mode != "shadow":
            raise ValueError("Lead Grading 第四阶段只允许 shadow_run。")
        if not isinstance(state.extracted_lead, LeadExtractionCandidate):
            state.extracted_lead = LeadExtractionCandidate(**state.extracted_lead)
        state.audit.update({"agent_mode": "shadow", "source_url": state.extracted_lead.source_url})
        self.set_node_summary(state, "load_extracted_lead", {"source_url": state.extracted_lead.source_url})
        return state

    def score_lead_signals(self, state: LeadGradingGraphState) -> LeadGradingGraphState:
        self.mark("score_lead_signals")
        lead = self.lead(state)
        state.signal_score = 0
        state.reasons = []
        state.triggered_rules = []

        if lead.email.value and lead.phone.value:
            state.signal_score += 35
            state.reasons.append("联系方式完整")
            state.triggered_rules.append("complete_contact")
        elif lead.email.value or lead.phone.value:
            state.signal_score += 18
            state.reasons.append("联系方式部分完整")
            state.triggered_rules.append("partial_contact")
        else:
            state.reasons.append("联系方式缺失")
            state.triggered_rules.append("contact_missing")

        if lead.export_intent.value:
            state.signal_score += 30
            state.reasons.append("出口意向明确")
            state.triggered_rules.append("export_intent_present")

        if lead.vehicle_interest.value:
            state.signal_score += 20
            state.reasons.append("车型兴趣明确")
            state.triggered_rules.append("vehicle_interest_present")

        if lead.company_name.value and lead.website.value:
            state.signal_score += 10
            state.reasons.append("公司名称和官网可核验")
            state.triggered_rules.append("company_website_present")

        state.recommended_grade, state.status_route, state.confidence_score = self.grade_from_score(state.signal_score)
        self.set_node_summary(
            state,
            "score_lead_signals",
            {"signal_score": state.signal_score, "base_grade": state.recommended_grade},
        )
        return state

    def apply_hard_rules(self, state: LeadGradingGraphState) -> LeadGradingGraphState:
        self.mark("apply_hard_rules")
        state.audit["hard_rules_applied"] = False
        risk_flags = set(state.risk_flags)

        if "forbidden_source" in risk_flags:
            self.override(state, grade="Invalid", route="risk_blocked", rule="forbidden_source", reason="Forbidden 来源命中，禁止进入可用线索。")
        elif "do_not_contact" in risk_flags:
            self.override(state, grade="Invalid", route="risk_blocked", rule="do_not_contact", reason="命中勿扰规则，禁止触达和晋级。")
        elif "existing_invalid" in risk_flags:
            self.override(state, grade="Invalid", route="risk_blocked", rule="existing_invalid", reason="现有记录为 Invalid，第四阶段不得自动恢复。")
        elif "high_risk_source" in risk_flags:
            self.override(state, grade="Watch", route="needs_manual_risk_review", rule="high_risk_source", reason="High 风险来源只允许人工风险复核。")
        elif "existing_watch" in risk_flags:
            self.override(state, grade="Watch", route="needs_manual_risk_review", rule="existing_watch", reason="现有记录为 Watch，需要人工复核后再处理。")
        elif "c_level_compliance_review" in risk_flags:
            self.override(state, grade="C", route="needs_compliance_review", rule="c_level_compliance_review", reason="命中 C 级合规复核规则。")
        elif "contact_missing" in state.triggered_rules:
            self.override(state, grade="C", route="needs_compliance_review", rule="contact_missing", reason="联系方式缺失，需要合规复核。")

        self.set_node_summary(
            state,
            "apply_hard_rules",
            {"hard_rules_applied": state.audit["hard_rules_applied"], "triggered_rules": state.triggered_rules},
        )
        return state

    def explain_grade_delta(self, state: LeadGradingGraphState) -> LeadGradingGraphState:
        self.mark("explain_grade_delta")
        if state.existing_grade and state.existing_grade != state.recommended_grade:
            state.explanations["grade_delta_from_existing"] = (
                f"现有等级为 {state.existing_grade}，shadow 建议为 {state.recommended_grade}；"
                f"差异原因：{'；'.join(state.reasons)}"
            )
        else:
            state.explanations["grade_delta_from_existing"] = "现有等级为空或与 shadow 建议一致。"
        self.set_node_summary(state, "explain_grade_delta", {"explanation_count": len(state.explanations)})
        return state

    def output_shadow_grading(self, state: LeadGradingGraphState) -> LeadGradingGraphState:
        self.mark("output_shadow_grading")
        output_table = self.boundary.validate_output_table("shadow_lead_grading_suggestions")
        lead = self.lead(state)
        state.suggestion = LeadGradingSuggestion(
            source_url=lead.source_url,
            recommended_grade=state.recommended_grade or "C",
            status_route=state.status_route or "needs_compliance_review",
            confidence_score=state.confidence_score,
            reasons=state.reasons or ["无可用评分原因。"],
            triggered_rules=state.triggered_rules or ["manual_review_required"],
            explanations=state.explanations,
            auto_promote_customer=False,
        )
        state.audit.update(
            {
                "writes_core_tables": False,
                "output_table": output_table,
                "written_tables": [output_table],
                "source_urls": [lead.source_url],
            }
        )
        self.set_node_summary(state, "output_shadow_grading", {"suggestion_count": 1})
        return state

    def run(self, state: LeadGradingGraphState) -> LeadGradingGraphResult:
        invoked_state = self.compiled_graph.invoke(state)
        state = self._state_from_graph_result(invoked_state)
        output = LeadGradingAgentOutput(
            schema_version="phase4.agent.lead_grading.v1",
            grading_run_id=state.grading_run_id,
            agent_mode="shadow",
            suggestions=[state.suggestion] if state.suggestion else [],
            audit=state.audit,
        )
        return LeadGradingGraphResult(output=output, executed_nodes=list(self.executed_nodes))

    def _state_from_graph_result(self, result: LeadGradingGraphState | dict[str, Any]) -> LeadGradingGraphState:
        if isinstance(result, LeadGradingGraphState):
            return result
        return LeadGradingGraphState(
            grading_run_id=result["grading_run_id"],
            extracted_lead=(
                result["extracted_lead"]
                if isinstance(result.get("extracted_lead"), LeadExtractionCandidate)
                else LeadExtractionCandidate(**result["extracted_lead"])
            ),
            agent_mode=result.get("agent_mode") or "shadow",
            risk_flags=list(result.get("risk_flags") or []),
            existing_grade=result.get("existing_grade"),
            signal_score=int(result.get("signal_score") or 0),
            reasons=list(result.get("reasons") or []),
            triggered_rules=list(result.get("triggered_rules") or []),
            recommended_grade=result.get("recommended_grade"),
            status_route=result.get("status_route"),
            confidence_score=float(result.get("confidence_score") or 0),
            explanations=dict(result.get("explanations") or {}),
            suggestion=(
                result["suggestion"]
                if isinstance(result.get("suggestion"), LeadGradingSuggestion)
                else LeadGradingSuggestion(**result["suggestion"])
                if result.get("suggestion")
                else None
            ),
            audit=dict(result.get("audit") or {}),
        )

    @staticmethod
    def lead(state: LeadGradingGraphState) -> LeadExtractionCandidate:
        if not isinstance(state.extracted_lead, LeadExtractionCandidate):
            state.extracted_lead = LeadExtractionCandidate(**state.extracted_lead)
        return state.extracted_lead

    @staticmethod
    def grade_from_score(score: int) -> tuple[str, str, float]:
        if score >= 90:
            return "A", "ready_for_manual_review", 0.95
        if score >= 60:
            return "B", "ready_for_manual_review", 0.78
        return "C", "needs_compliance_review", 0.62

    @staticmethod
    def override(
        state: LeadGradingGraphState,
        *,
        grade: str,
        route: str,
        rule: str,
        reason: str,
    ) -> None:
        state.recommended_grade = grade
        state.status_route = route
        state.confidence_score = 1.0 if grade in {"Invalid", "Watch"} else min(state.confidence_score, 0.7)
        if rule not in state.triggered_rules:
            state.triggered_rules.append(rule)
        if reason not in state.reasons:
            state.reasons.append(reason)
        state.audit["hard_rules_applied"] = True
