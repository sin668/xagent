from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Phase4AgentMetrics:
    agent_name: str
    sample_count: int
    metrics: dict[str, str]
    source_report: str
    notes: str


class Phase4SampleMetricsService:
    @classmethod
    def demo_metrics(cls) -> list[Phase4AgentMetrics]:
        return [
            Phase4AgentMetrics(
                agent_name="Source Discovery",
                sample_count=30,
                metrics={
                    "URL 有效率": "90%",
                    "重复率": "10%",
                    "风险分级一致率": "80%",
                    "证据完整率": "90%",
                },
                source_report="docs/reports/phase-4/source-discovery-shadow-report.md",
                notes="来自 Source Discovery shadow 30 条样本对照报告。",
            ),
            Phase4AgentMetrics(
                agent_name="Lead Extraction",
                sample_count=30,
                metrics={
                    "schema 通过率": "96.67%",
                    "证据命中率": "93.33%",
                    "联系方式反编造通过率": "90%",
                    "字段完整度": "87.5%",
                },
                source_report="docs/reports/phase-4/lead-extraction-grading-shadow-report.md",
                notes="来自 Lead Extraction/Grading shadow 30 条样本对照报告中的抽取指标。",
            ),
            Phase4AgentMetrics(
                agent_name="Lead Grading",
                sample_count=30,
                metrics={
                    "等级一致率": "80%",
                    "硬规则一致率": "96.67%",
                    "C/Invalid/Watch 分流准确性": "96.67%",
                },
                source_report="docs/reports/phase-4/lead-extraction-grading-shadow-report.md",
                notes="来自 Lead Extraction/Grading shadow 30 条样本对照报告中的分级指标。",
            ),
            Phase4AgentMetrics(
                agent_name="Deep Enrichment",
                sample_count=20,
                metrics={
                    "字段候选有效率": "92%",
                    "人工接受率": "78%",
                    "无证据候选率": "0%",
                },
                source_report="docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md",
                notes="第四阶段小范围运行基线样本指标；后续由 P4-E7-S4 总结报告统一评估。",
            ),
            Phase4AgentMetrics(
                agent_name="Lead Cleanup",
                sample_count=20,
                metrics={
                    "重复建议准确率": "88%",
                    "错误合并建议数": "0",
                    "人工拒绝率": "12%",
                },
                source_report="docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md",
                notes="第四阶段小范围运行基线样本指标；后续由 P4-E7-S4 总结报告统一评估。",
            ),
        ]

    @classmethod
    def summarize(cls, metrics: list[Phase4AgentMetrics]) -> dict:
        summary: dict[str, object] = {
            "agent_count": len(metrics),
            "total_sample_count": sum(item.sample_count for item in metrics),
        }
        for item in metrics:
            summary[cls.agent_key(item.agent_name)] = dict(item.metrics)
        return summary

    @classmethod
    def render_markdown(cls, *, metrics: list[Phase4AgentMetrics]) -> str:
        summary = cls.summarize(metrics)
        lines = [
            "# 第四阶段小范围运行样本指标汇总",
            "",
            "生成方式：汇总第四阶段各 Agent shadow/active 小范围运行样本指标，仅用于阶段评估。",
            "",
            "## 1. 范围说明",
            "",
            f"- Agent 数量：{summary['agent_count']}",
            f"- 样本总数：{summary['total_sample_count']}",
            "- 本报告不输出最终 Go/No-Go 结论；最终结论由 P4-E7-S4 汇总。",
            "- 指标只用于阶段评估，不自动调整 Agent 开关。",
            "- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。",
            "",
            "## 2. 指标总览",
            "",
            "| Agent | 样本数 | 指标 | 结果 | 来源 |",
            "|---|---:|---|---:|---|",
        ]
        for item in metrics:
            for metric_name, metric_value in item.metrics.items():
                lines.append(
                    f"| {item.agent_name} | {item.sample_count} | {metric_name} | {metric_value} | {item.source_report} |"
                )

        lines.extend(["", "## 3. 分 Agent 说明", ""])
        for item in metrics:
            lines.extend(
                [
                    f"### {item.agent_name}",
                    "",
                    f"- 样本数：{item.sample_count}",
                    f"- 来源：`{item.source_report}`",
                    f"- 说明：{item.notes}",
                    "",
                    "| 指标 | 结果 |",
                    "|---|---:|",
                ]
            )
            for metric_name, metric_value in item.metrics.items():
                lines.append(f"| {metric_name} | {metric_value} |")
            lines.append("")

        lines.extend(
            [
                "## 4. 使用边界",
                "",
                "- 本报告只汇总样本指标，不输出最终 Go/No-Go 结论。",
                "- 本报告不修改业务数据，不自动调整 Agent 开关。",
                "- Deep Enrichment 与 Lead Cleanup 指标为第四阶段小范围运行基线口径，后续需在 P4-E7-S4 中结合失败案例和人工审核结果复核。",
                "",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def agent_key(agent_name: str) -> str:
        return agent_name.lower().replace(" ", "_")
