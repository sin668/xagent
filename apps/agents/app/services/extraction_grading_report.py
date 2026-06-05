from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DifferenceType = Literal["等级差异", "硬规则不一致", "证据/联系方式差异", "一致"]


@dataclass(frozen=True)
class LeadExtractionGradingSampleResult:
    sample_id: str
    existing_grade: str
    shadow_grade: str
    status_route: str
    schema_passed: bool
    evidence_passed: bool
    contact_anti_fabrication_passed: bool
    present_field_count: int
    total_field_count: int
    grade_consistent: bool
    hard_rule_consistent: bool
    routing_accurate: bool
    difference_type: DifferenceType
    reason: str
    recommendation: str


class LeadExtractionGradingShadowReportService:
    report_title = "Lead Extraction/Grading shadow 对照报告"

    @classmethod
    def demo_sample_results(cls) -> list[LeadExtractionGradingSampleResult]:
        samples: list[LeadExtractionGradingSampleResult] = []
        for index in range(1, 31):
            samples.append(
                LeadExtractionGradingSampleResult(
                    sample_id=f"LEG-{index:02d}",
                    existing_grade="B",
                    shadow_grade="B",
                    status_route="ready_for_manual_review",
                    schema_passed=index != 4,
                    evidence_passed=index not in {8, 19},
                    contact_anti_fabrication_passed=index not in {11, 22, 28},
                    present_field_count=7,
                    total_field_count=8,
                    grade_consistent=index not in {5, 9, 14, 17, 21, 27},
                    hard_rule_consistent=index != 17,
                    routing_accurate=index != 17,
                    difference_type="一致",
                    reason="现有链路与 shadow 抽取分级基本一致。",
                    recommendation="继续纳入样本观察。",
                )
            )

        replacements = {
            5: ("等级差异", "现有链路为 B，shadow 因出口意向和车型兴趣建议 A。", "复核评分权重，确认 A 级阈值是否过宽。"),
            9: ("等级差异", "现有链路为 C，shadow 因联系方式完整建议 B。", "检查现有链路是否漏计联系方式完整性。"),
            14: ("等级差异", "现有链路为 B，shadow 因证据较弱建议 C。", "要求补充公开证据后再比较等级。"),
            17: ("硬规则不一致", "shadow 未按 Forbidden 规则分流到 Invalid/risk_blocked。", "作为阻塞问题处理，修正硬规则后才能考虑 active_run。"),
            19: ("证据/联系方式差异", "shadow 部分字段证据命中不足。", "补充证据命中校验样本，证据不足字段不得自动采纳。"),
            22: ("证据/联系方式差异", "shadow 联系方式反编造校验失败。", "联系方式必须出现在公开来源文本中，否则标记无效。"),
            27: ("等级差异", "现有链路为 Watch，shadow 建议 C。", "复核 Watch/Invalid 历史状态分流规则。"),
            28: ("证据/联系方式差异", "shadow 电话未在来源文本中命中。", "保持无效联系方式标记，不得写入 staging_leads。"),
        }
        for index, (difference_type, reason, recommendation) in replacements.items():
            old = samples[index - 1]
            samples[index - 1] = LeadExtractionGradingSampleResult(
                sample_id=old.sample_id,
                existing_grade="Invalid" if index == 17 else old.existing_grade,
                shadow_grade="B" if index == 17 else old.shadow_grade,
                status_route="ready_for_manual_review" if index == 17 else old.status_route,
                schema_passed=old.schema_passed,
                evidence_passed=old.evidence_passed,
                contact_anti_fabrication_passed=old.contact_anti_fabrication_passed,
                present_field_count=old.present_field_count,
                total_field_count=old.total_field_count,
                grade_consistent=old.grade_consistent,
                hard_rule_consistent=old.hard_rule_consistent,
                routing_accurate=old.routing_accurate,
                difference_type=difference_type,  # type: ignore[arg-type]
                reason=reason,
                recommendation=recommendation,
            )
        return samples

    @classmethod
    def summarize(cls, sample_results: list[LeadExtractionGradingSampleResult]) -> dict:
        sample_count = len(sample_results)
        if sample_count == 0:
            raise ValueError("Lead Extraction/Grading shadow 报告至少需要 1 条样本。")

        total_fields = sum(item.total_field_count for item in sample_results)
        present_fields = sum(item.present_field_count for item in sample_results)
        hard_rule_mismatch_count = sum(1 for item in sample_results if not item.hard_rule_consistent)
        summary = {
            "sample_count": sample_count,
            "schema_pass_rate": cls.rate(sum(1 for item in sample_results if item.schema_passed), sample_count),
            "evidence_hit_rate": cls.rate(sum(1 for item in sample_results if item.evidence_passed), sample_count),
            "contact_anti_fabrication_pass_rate": cls.rate(
                sum(1 for item in sample_results if item.contact_anti_fabrication_passed),
                sample_count,
            ),
            "field_completeness_rate": cls.rate(present_fields, total_fields),
            "grade_consistency_rate": cls.rate(sum(1 for item in sample_results if item.grade_consistent), sample_count),
            "hard_rule_consistency_rate": cls.rate(
                sum(1 for item in sample_results if item.hard_rule_consistent),
                sample_count,
            ),
            "routing_accuracy_rate": cls.rate(sum(1 for item in sample_results if item.routing_accurate), sample_count),
            "hard_rule_mismatch_count": hard_rule_mismatch_count,
        }
        summary["recommendation"] = (
            "No-Go：存在硬规则不一致，禁止进入 active_run。"
            if hard_rule_mismatch_count
            else "Go：硬规则一致率 100%，可进入下一轮更大样本 shadow。"
        )
        return summary

    @staticmethod
    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4)

    @classmethod
    def render_markdown(cls, *, sample_results: list[LeadExtractionGradingSampleResult]) -> str:
        summary = cls.summarize(sample_results)
        grouped = cls.group_differences(sample_results)
        lines = [
            f"# {cls.report_title}",
            "",
            "生成方式：由 `apps/agents` Lead Extraction/Grading shadow 样本数据生成，报告只用于第四阶段对照验证。",
            "",
            "## 1. 结论",
            "",
            f"- 样本数：{summary['sample_count']}",
            f"- 建议：{summary['recommendation']}",
            "- 本报告不等同于生产切换批准；Lead Extraction/Grading 第四阶段仍只允许 shadow_run。",
            "",
            "## 2. 指标总览",
            "",
            "| 指标 | 结果 | 说明 |",
            "|---|---:|---|",
            f"| schema 通过率 | {summary['schema_pass_rate']:.2%} | schema 通过样本 / 样本数 |",
            f"| 证据命中率 | {summary['evidence_hit_rate']:.2%} | 证据命中样本 / 样本数 |",
            f"| 联系方式反编造通过率 | {summary['contact_anti_fabrication_pass_rate']:.0%} | 联系方式通过反编造校验 / 样本数 |",
            f"| 字段完整度 | {summary['field_completeness_rate']:.1%} | 已抽取字段 / 应抽取字段 |",
            f"| 等级一致率 | {summary['grade_consistency_rate']:.0%} | shadow 等级与现有链路一致 / 样本数 |",
            f"| 硬规则一致率 | {summary['hard_rule_consistency_rate']:.2%} | 硬规则分流一致 / 样本数 |",
            f"| C/Invalid/Watch 分流准确性 | {summary['routing_accuracy_rate']:.2%} | C/Invalid/Watch 分流正确 / 样本数 |",
            f"| 硬规则不一致数 | {summary['hard_rule_mismatch_count']} | 必须列为阻塞问题 |",
            "",
            "## 3. 主要差异",
            "",
        ]
        for difference_type in ("等级差异", "硬规则不一致", "证据/联系方式差异"):
            lines.extend(cls.render_difference_table(difference_type, grouped.get(difference_type, [])))
            lines.append("")

        lines.extend(
            [
                "## 4. 风险与处理建议",
                "",
                "- 硬规则不一致必须作为阻塞问题处理，修正前不得进入 active_run。",
                "- 联系方式必须在公开来源文本中命中，否则标记为无效联系方式。",
                "- schema 或证据不足样本不得自动写入 `staging_leads`。",
                "- 等级差异必须保留可解释原因，不得只输出等级结论。",
                "",
                "## 5. 样本明细",
                "",
                "| 样本 | 差异类型 | 现有等级 | shadow 等级 | 状态分流 | schema 通过 | 证据命中 | 反编造通过 | 硬规则一致 | 分流准确 | 原因 | 处理建议 |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for sample in sample_results:
            lines.append(
                "| {sample_id} | {difference_type} | {existing_grade} | {shadow_grade} | {status_route} | {schema_passed} | {evidence_passed} | {contact_passed} | {hard_rule_consistent} | {routing_accurate} | {reason} | {recommendation} |".format(
                    sample_id=sample.sample_id,
                    difference_type=sample.difference_type,
                    existing_grade=sample.existing_grade,
                    shadow_grade=sample.shadow_grade,
                    status_route=sample.status_route,
                    schema_passed=cls.yes_no(sample.schema_passed),
                    evidence_passed=cls.yes_no(sample.evidence_passed),
                    contact_passed=cls.yes_no(sample.contact_anti_fabrication_passed),
                    hard_rule_consistent=cls.yes_no(sample.hard_rule_consistent),
                    routing_accurate=cls.yes_no(sample.routing_accurate),
                    reason=sample.reason,
                    recommendation=sample.recommendation,
                )
            )
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def group_differences(sample_results: list[LeadExtractionGradingSampleResult]) -> dict[str, list[LeadExtractionGradingSampleResult]]:
        grouped: dict[str, list[LeadExtractionGradingSampleResult]] = {}
        for sample in sample_results:
            if sample.difference_type == "一致":
                continue
            grouped.setdefault(sample.difference_type, []).append(sample)
        return grouped

    @classmethod
    def render_difference_table(cls, difference_type: str, samples: list[LeadExtractionGradingSampleResult]) -> list[str]:
        lines = [
            f"### {difference_type}",
            "",
            "| 差异类型 | 样本 | 可解释原因 | 处理建议 |",
            "|---|---|---|---|",
        ]
        if not samples:
            lines.append(f"| {difference_type} | 无 | 当前 30 条样本未发现该类差异。 | 继续观察。 |")
            return lines
        for sample in samples:
            lines.append(f"| {difference_type} | {sample.sample_id} | {sample.reason} | {sample.recommendation} |")
        return lines

    @staticmethod
    def yes_no(value: bool) -> str:
        return "是" if value else "否"
