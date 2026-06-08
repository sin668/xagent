from pathlib import Path

from app.services.extraction_grading_report import LeadExtractionGradingShadowReportService


def test_extraction_grading_shadow_report_renders_required_metrics_and_30_samples() -> None:
    report = LeadExtractionGradingShadowReportService().render_markdown(
        sample_results=LeadExtractionGradingShadowReportService.demo_sample_results()
    )

    assert "# Lead Extraction/Grading shadow 对照报告" in report
    assert "样本数：30" in report
    assert "schema 通过率" in report
    assert "证据命中率" in report
    assert "联系方式反编造通过率" in report
    assert "字段完整度" in report
    assert "等级一致率" in report
    assert "硬规则一致率" in report
    assert "C/Invalid/Watch 分流准确性" in report
    assert "硬规则不一致数" in report
    assert "| 等级差异 |" in report
    assert "| 硬规则不一致 |" in report
    assert "| 证据/联系方式差异 |" in report
    assert "处理建议" in report
    assert "本报告不等同于生产切换批准" in report


def test_extraction_grading_shadow_report_metrics_are_computed_from_samples() -> None:
    service = LeadExtractionGradingShadowReportService()
    samples = service.demo_sample_results()
    summary = service.summarize(samples)

    assert summary["sample_count"] == 30
    assert summary["schema_pass_rate"] == 0.9667
    assert summary["evidence_hit_rate"] == 0.9333
    assert summary["contact_anti_fabrication_pass_rate"] == 0.9
    assert summary["field_completeness_rate"] == 0.875
    assert summary["grade_consistency_rate"] == 0.8
    assert summary["hard_rule_consistency_rate"] == 0.9667
    assert summary["routing_accuracy_rate"] == 0.9667
    assert summary["hard_rule_mismatch_count"] == 1
    assert summary["recommendation"] == "No-Go：存在硬规则不一致，禁止进入 active_run。"


def test_extraction_grading_shadow_report_file_matches_generated_content() -> None:
    report_path = Path(__file__).resolve().parents[3] / "docs" / "reports" / "phase-4" / "lead-extraction-grading-shadow-report.md"
    expected = LeadExtractionGradingShadowReportService().render_markdown(
        sample_results=LeadExtractionGradingShadowReportService.demo_sample_results()
    )

    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == expected
