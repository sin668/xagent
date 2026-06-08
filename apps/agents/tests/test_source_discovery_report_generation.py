from pathlib import Path

from app.services.source_discovery_report import SourceDiscoveryShadowReportService


def test_source_discovery_shadow_report_renders_required_metrics_and_30_samples() -> None:
    report = SourceDiscoveryShadowReportService().render_markdown(
        sample_results=SourceDiscoveryShadowReportService.demo_sample_results()
    )

    assert "# Source Discovery shadow 对照报告" in report
    assert "样本数：30" in report
    assert "URL 有效率" in report
    assert "重复率" in report
    assert "风险分级一致率" in report
    assert "证据完整率" in report
    assert "Forbidden 误放数" in report
    assert "| 新增来源 |" in report
    assert "| 缺失来源 |" in report
    assert "| 风险分级差异 |" in report
    assert "| 证据差异 |" in report
    assert "处理建议" in report
    assert "本报告不等同于生产切换批准" in report


def test_source_discovery_shadow_report_metrics_are_computed_from_samples() -> None:
    service = SourceDiscoveryShadowReportService()
    samples = service.demo_sample_results()
    summary = service.summarize(samples)

    assert summary["sample_count"] == 30
    assert summary["valid_url_rate"] == 0.9
    assert summary["duplicate_rate"] == 0.1
    assert summary["risk_consistency_rate"] == 0.8
    assert summary["evidence_completeness_rate"] == 0.9
    assert summary["forbidden_leak_count"] == 1
    assert summary["recommendation"] == "No-Go：存在 Forbidden 误放，禁止进入 active_run。"


def test_source_discovery_shadow_report_file_matches_generated_content() -> None:
    report_path = Path(__file__).resolve().parents[3] / "docs" / "reports" / "phase-4" / "source-discovery-shadow-report.md"
    expected = SourceDiscoveryShadowReportService().render_markdown(
        sample_results=SourceDiscoveryShadowReportService.demo_sample_results()
    )

    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == expected
