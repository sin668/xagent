from __future__ import annotations

from dataclasses import dataclass


NON_RETRYABLE_COMPLIANCE_ERROR_TYPES = {
    "schema_validation_error",
    "evidence_validation_error",
    "forbidden_source_error",
    "hard_rule_conflict",
    "risk_blocked",
    "contract_mismatch",
}


@dataclass(frozen=True)
class FailedCase:
    case_id: str
    agent_type: str
    error_type: str
    error_category: str
    retryable: bool
    source: str
    symptom: str
    root_cause: str
    recommendation: str
    follow_up_story: str


class FailedCaseClassificationService:
    @classmethod
    def demo_failed_cases(cls) -> list[FailedCase]:
        return [
            FailedCase(
                case_id="FC-SD-001",
                agent_type="Source Discovery",
                error_type="forbidden_source_error",
                error_category="Forbidden 来源",
                retryable=False,
                source="docs/reports/phase-4/source-discovery-shadow-report.md#SD-17",
                symptom="shadow 将登录墙来源输出为有效候选。",
                root_cause="Forbidden 过滤节点未在候选输出前形成硬阻断。",
                recommendation="不可自动重试；先修正 Forbidden 过滤和风险阻断规则，再重新进入 shadow 对照。",
                follow_up_story="后续 Story：补充 Forbidden 来源回归样本和阻断规则验收。",
            ),
            FailedCase(
                case_id="FC-LE-001",
                agent_type="Lead Extraction",
                error_type="schema_validation_error",
                error_category="schema 不满足",
                retryable=False,
                source="docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-04",
                symptom="抽取结果缺少必填字段或字段类型不满足 schema。",
                root_cause="LLM 输出未完全遵守结构化契约，且缺少 schema 修复前置校验。",
                recommendation="不可自动重试成功；先收紧 schema validator 和 prompt 输出格式，再人工复核失败样本。",
                follow_up_story="后续 Story：增加结构化输出修复提示词和 schema 回归集。",
            ),
            FailedCase(
                case_id="FC-LE-002",
                agent_type="Lead Extraction",
                error_type="evidence_validation_error",
                error_category="证据缺失",
                retryable=False,
                source="docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-19",
                symptom="字段有抽取值，但缺少公开来源证据命中。",
                root_cause="证据引用节点未能拒绝弱证据字段。",
                recommendation="不可自动重试；证据不足字段不得自动采纳，需补充来源文本命中或缺失原因。",
                follow_up_story="后续 Story：扩充证据命中校验样本并强化字段级缺失原因。",
            ),
            FailedCase(
                case_id="FC-LE-003",
                agent_type="Lead Extraction",
                error_type="evidence_validation_error",
                error_category="证据缺失",
                retryable=False,
                source="docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-22",
                symptom="联系方式反编造校验失败。",
                root_cause="联系方式未在公开来源文本中命中。",
                recommendation="不可自动重试；联系方式必须保留无效标记，不得写入 staging_leads。",
                follow_up_story="后续 Story：增加联系方式反编造负样本和来源定位提示。",
            ),
            FailedCase(
                case_id="FC-LG-001",
                agent_type="Lead Grading",
                error_type="hard_rule_conflict",
                error_category="硬规则冲突",
                retryable=False,
                source="docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-17",
                symptom="shadow 未按 Forbidden 规则分流到 Invalid/risk_blocked。",
                root_cause="LLM 分级结论覆盖了合规硬规则。",
                recommendation="不可自动重试；合规硬规则失败不得归类为可自动重试成功的问题，必须先修正硬规则优先级。",
                follow_up_story="后续 Story：补充硬规则优先级回归和 risk_blocked 分流审计。",
            ),
            FailedCase(
                case_id="FC-DE-001",
                agent_type="Deep Enrichment",
                error_type="provider_rate_limited",
                error_category="外部服务暂态失败",
                retryable=True,
                source="agent_service_runs retry policy",
                symptom="字段候选生成期间 LLM provider 返回限流。",
                root_cause="外部 provider 临时容量限制。",
                recommendation="可按 retry policy 自动重试；不得绕过人工审核写入字段候选。",
                follow_up_story="后续 Story：观察 provider 限流频率，必要时调整并发和退避参数。",
            ),
            FailedCase(
                case_id="FC-LC-001",
                agent_type="Lead Cleanup",
                error_type="timeout_error",
                error_category="外部服务暂态失败",
                retryable=True,
                source="agent_service_runs retry policy",
                symptom="清洗建议生成超时。",
                root_cause="LLM 请求或上游网络暂态超时。",
                recommendation="可按 retry policy 自动重试；不得自动归并、自动恢复 Invalid 或自动触达。",
                follow_up_story="后续 Story：观察超时节点和输入规模，必要时拆分清洗建议生成。",
            ),
        ]

    @classmethod
    def summarize(cls, cases: list[FailedCase]) -> dict:
        if not cases:
            raise ValueError("失败案例整理至少需要 1 条案例。")

        agent_types = sorted({case.agent_type for case in cases})
        error_types = sorted({case.error_type for case in cases})
        categories = sorted({case.error_category for case in cases})
        return {
            "case_count": len(cases),
            "agent_types": agent_types,
            "error_types": error_types,
            "categories": categories,
            "retryable_count": sum(1 for case in cases if case.retryable),
            "non_retryable_count": sum(1 for case in cases if not case.retryable),
        }

    @classmethod
    def render_markdown(cls, *, cases: list[FailedCase]) -> str:
        summary = cls.summarize(cases)
        lines = [
            "# 第四阶段失败案例与不可重试错误整理",
            "",
            "生成方式：汇总 `agent_service_runs`、节点 trace、Source Discovery 对照报告和 Lead Extraction/Grading 对照报告中的失败信号，按 Agent 类型、错误类型、是否可重试分类。",
            "",
            "## 1. 范围说明",
            "",
            f"- 失败案例数：{summary['case_count']}",
            f"- 涉及 Agent：{', '.join(summary['agent_types'])}",
            f"- 可重试案例数：{summary['retryable_count']}",
            f"- 不可重试案例数：{summary['non_retryable_count']}",
            "- 本报告不自动修改历史 run 状态。",
            "- 本报告不自动重跑失败任务。",
            "- 本报告不输出最终 Go/No-Go 结论；最终结论由 P4-E7-S4 汇总。",
            "- 合规硬规则失败不得归类为可自动重试成功的问题。",
            "",
            "## 2. 不可重试错误类别",
            "",
            "| 类别 | error_type | 处理原则 |",
            "|---|---|---|",
            "| schema 不满足 | `schema_validation_error` | 修正 schema validator、prompt 输出格式或输入数据后再进入 shadow；不得靠自动重试视为成功。 |",
            "| 证据缺失 | `evidence_validation_error` | 缺少公开证据命中的字段不得自动采纳，必须补充证据或缺失原因。 |",
            "| Forbidden 来源 | `forbidden_source_error`、`risk_blocked` | Forbidden 或高风险来源必须硬阻断，修正过滤规则前不得进入 active_run。 |",
            "| 硬规则冲突 | `hard_rule_conflict`、`contract_mismatch` | 合规硬规则优先级高于 LLM 判断，冲突时不得自动重试绕过。 |",
            "",
            "## 3. 分类总览",
            "",
            "| Agent | 错误类型 | 类别 | 是否可重试 | 案例 | 来源 |",
            "|---|---|---|---|---|---|",
        ]
        for case in cases:
            lines.append(
                f"| {case.agent_type} | `{case.error_type}` | {case.error_category} | {cls.yes_no(case.retryable)} | {case.case_id} | {case.source} |"
            )

        lines.extend(["", "## 4. 失败案例明细", ""])
        for case in cases:
            lines.extend(
                [
                    f"### {case.case_id}：{case.agent_type} / {case.error_category}",
                    "",
                    f"- 错误类型：`{case.error_type}`",
                    f"- 是否可重试：{cls.yes_no(case.retryable)}",
                    f"- 来源：`{case.source}`",
                    f"- 现象：{case.symptom}",
                    f"- 根因判断：{case.root_cause}",
                    f"- 修正建议：{case.recommendation}",
                    f"- 后续建议：{case.follow_up_story}",
                    "",
                ]
            )

        lines.extend(
            [
                "## 5. 使用边界",
                "",
                "- 失败案例整理只用于改进错误分类、提示词、数据质量和后续迁移策略。",
                "- 不自动恢复 Invalid、不自动重跑、不自动触达。",
                "- 不自动晋级、不自动归并、不自动调整 Agent 开关。",
                "- 可重试仅限暂态 provider、限流或网络类错误；schema、证据、Forbidden、硬规则冲突均按不可重试处理。",
                "",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def yes_no(value: bool) -> str:
        return "是" if value else "否"


def is_non_retryable_compliance_error(error_type: str) -> bool:
    return error_type in NON_RETRYABLE_COMPLIANCE_ERROR_TYPES
