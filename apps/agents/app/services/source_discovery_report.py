from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DifferenceType = Literal["新增来源", "缺失来源", "风险分级差异", "证据差异", "一致"]


@dataclass(frozen=True)
class SourceDiscoverySampleResult:
    sample_id: str
    existing_url: str | None
    shadow_url: str | None
    url_valid: bool
    duplicate: bool
    risk_match: bool
    evidence_complete: bool
    forbidden_leak: bool
    difference_type: DifferenceType
    reason: str
    recommendation: str


class SourceDiscoveryShadowReportService:
    report_title = "Source Discovery shadow 对照报告"

    @classmethod
    def demo_sample_results(cls) -> list[SourceDiscoverySampleResult]:
        samples: list[SourceDiscoverySampleResult] = []
        for index in range(1, 31):
            samples.append(
                SourceDiscoverySampleResult(
                    sample_id=f"SD-{index:02d}",
                    existing_url=f"https://existing-{index:02d}.example.ru",
                    shadow_url=f"https://shadow-{index:02d}.example.ru",
                    url_valid=index not in {4, 18, 29},
                    duplicate=index in {6, 12, 24},
                    risk_match=index not in {5, 9, 14, 17, 21, 27},
                    evidence_complete=index not in {8, 19, 26},
                    forbidden_leak=index == 17,
                    difference_type="一致",
                    reason="现有链路与 shadow 输出基本一致。",
                    recommendation="继续纳入样本观察。",
                )
            )

        replacements = {
            3: ("新增来源", "shadow 发现公开目录页，现有链路未覆盖。", "补充现有来源发现 query，并人工复核该目录可信度。"),
            7: ("缺失来源", "现有链路命中官网子页面，shadow 未召回。", "检查 shadow 查询词是否过窄。"),
            9: ("风险分级差异", "现有链路为 Medium，shadow 判断为 High。", "人工复核平台政策，High 来源不得自动抽取。"),
            17: ("风险分级差异", "shadow 将登录墙来源输出为有效候选。", "作为阻塞风险处理，修正 Forbidden 过滤后才能考虑 active。"),
            19: ("证据差异", "shadow 候选缺少可解释证据摘要。", "要求补充公开证据摘要，否则不得进入有效候选。"),
            24: ("新增来源", "shadow 输出与既有候选等价，属于重复来源。", "保留去重标记，不写入 lead_source_candidates。"),
        }
        for index, (difference_type, reason, recommendation) in replacements.items():
            old = samples[index - 1]
            samples[index - 1] = SourceDiscoverySampleResult(
                sample_id=old.sample_id,
                existing_url=old.existing_url,
                shadow_url=old.shadow_url,
                url_valid=old.url_valid,
                duplicate=old.duplicate,
                risk_match=old.risk_match,
                evidence_complete=old.evidence_complete,
                forbidden_leak=old.forbidden_leak,
                difference_type=difference_type,  # type: ignore[arg-type]
                reason=reason,
                recommendation=recommendation,
            )
        return samples

    @classmethod
    def summarize(cls, sample_results: list[SourceDiscoverySampleResult]) -> dict:
        sample_count = len(sample_results)
        if sample_count == 0:
            raise ValueError("Source Discovery shadow 报告至少需要 1 条样本。")

        forbidden_leak_count = sum(1 for item in sample_results if item.forbidden_leak)
        summary = {
            "sample_count": sample_count,
            "valid_url_rate": cls.rate(sum(1 for item in sample_results if item.url_valid), sample_count),
            "duplicate_rate": cls.rate(sum(1 for item in sample_results if item.duplicate), sample_count),
            "risk_consistency_rate": cls.rate(sum(1 for item in sample_results if item.risk_match), sample_count),
            "evidence_completeness_rate": cls.rate(sum(1 for item in sample_results if item.evidence_complete), sample_count),
            "forbidden_leak_count": forbidden_leak_count,
        }
        summary["recommendation"] = (
            "No-Go：存在 Forbidden 误放，禁止进入 active_run。"
            if forbidden_leak_count
            else "Go：未发现 Forbidden 误放，可进入下一轮更大样本 shadow。"
        )
        return summary

    @staticmethod
    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4)

    @classmethod
    def render_markdown(cls, *, sample_results: list[SourceDiscoverySampleResult]) -> str:
        summary = cls.summarize(sample_results)
        grouped = cls.group_differences(sample_results)
        lines = [
            f"# {cls.report_title}",
            "",
            "生成方式：由 `apps/agents` Source Discovery shadow 样本数据生成，报告只用于第四阶段对照验证。",
            "",
            "## 1. 结论",
            "",
            f"- 样本数：{summary['sample_count']}",
            f"- 建议：{summary['recommendation']}",
            "- 本报告不等同于生产切换批准；Source Discovery 第四阶段仍只允许 shadow_run。",
            "",
            "## 2. 指标总览",
            "",
            "| 指标 | 结果 | 说明 |",
            "|---|---:|---|",
            f"| URL 有效率 | {summary['valid_url_rate']:.0%} | 有效 URL / 样本数 |",
            f"| 重复率 | {summary['duplicate_rate']:.0%} | 重复或等价来源 / 样本数 |",
            f"| 风险分级一致率 | {summary['risk_consistency_rate']:.0%} | 现有链路与 shadow 风险一致 / 样本数 |",
            f"| 证据完整率 | {summary['evidence_completeness_rate']:.0%} | shadow 候选具备证据摘要 / 样本数 |",
            f"| Forbidden 误放数 | {summary['forbidden_leak_count']} | Forbidden 来源进入 shadow 有效候选的数量 |",
            "",
            "## 3. 主要差异",
            "",
        ]
        for difference_type in ("新增来源", "缺失来源", "风险分级差异", "证据差异"):
            lines.extend(cls.render_difference_table(difference_type, grouped.get(difference_type, [])))
            lines.append("")

        lines.extend(
            [
                "## 4. 风险与处理建议",
                "",
                "- Forbidden 误放必须作为阻塞风险处理，修正过滤规则前不得进入 active_run。",
                "- High 风险来源只允许进入人工复核，不得直接进入自动抽取。",
                "- 证据缺失样本必须补充公开证据摘要，否则不得作为有效来源。",
                "- 重复来源只保留对照标记，不写入 `lead_source_candidates`。",
                "",
                "## 5. 样本明细",
                "",
                "| 样本 | 差异类型 | URL 有效 | 重复 | 风险一致 | 证据完整 | Forbidden 误放 | 原因 | 处理建议 |",
                "|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for sample in sample_results:
            lines.append(
                "| {sample_id} | {difference_type} | {url_valid} | {duplicate} | {risk_match} | {evidence_complete} | {forbidden_leak} | {reason} | {recommendation} |".format(
                    sample_id=sample.sample_id,
                    difference_type=sample.difference_type,
                    url_valid=cls.yes_no(sample.url_valid),
                    duplicate=cls.yes_no(sample.duplicate),
                    risk_match=cls.yes_no(sample.risk_match),
                    evidence_complete=cls.yes_no(sample.evidence_complete),
                    forbidden_leak=cls.yes_no(sample.forbidden_leak),
                    reason=sample.reason,
                    recommendation=sample.recommendation,
                )
            )
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def group_differences(sample_results: list[SourceDiscoverySampleResult]) -> dict[str, list[SourceDiscoverySampleResult]]:
        grouped: dict[str, list[SourceDiscoverySampleResult]] = {}
        for sample in sample_results:
            if sample.difference_type == "一致":
                continue
            grouped.setdefault(sample.difference_type, []).append(sample)
        return grouped

    @classmethod
    def render_difference_table(cls, difference_type: str, samples: list[SourceDiscoverySampleResult]) -> list[str]:
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
