from pathlib import Path

from app.services.phase4_metrics import Phase4SampleMetricsService


def test_phase4_sample_metrics_report_renders_all_agent_metric_groups() -> None:
    report = Phase4SampleMetricsService().render_markdown(
        metrics=Phase4SampleMetricsService.demo_metrics()
    )

    assert "# 第四阶段小范围运行样本指标汇总" in report
    assert "Source Discovery" in report
    assert "URL 有效率" in report
    assert "重复率" in report
    assert "风险分级一致率" in report
    assert "证据完整率" in report
    assert "Lead Extraction" in report
    assert "schema 通过率" in report
    assert "证据命中率" in report
    assert "联系方式反编造通过率" in report
    assert "字段完整度" in report
    assert "Lead Grading" in report
    assert "等级一致率" in report
    assert "硬规则一致率" in report
    assert "C/Invalid/Watch 分流准确性" in report
    assert "Deep Enrichment" in report
    assert "字段候选有效率" in report
    assert "人工接受率" in report
    assert "无证据候选率" in report
    assert "Lead Cleanup" in report
    assert "重复建议准确率" in report
    assert "错误合并建议数" in report
    assert "人工拒绝率" in report
    assert "本报告不输出最终 Go/No-Go 结论" in report
    assert "不自动调整 Agent 开关" in report


def test_phase4_sample_metrics_summary_values_are_computed_from_demo_metrics() -> None:
    service = Phase4SampleMetricsService()
    metrics = service.demo_metrics()
    summary = service.summarize(metrics)

    assert summary["agent_count"] == 5
    assert summary["total_sample_count"] == 130
    assert summary["source_discovery"]["URL 有效率"] == "90%"
    assert summary["source_discovery"]["证据完整率"] == "90%"
    assert summary["lead_extraction"]["schema 通过率"] == "96.67%"
    assert summary["lead_extraction"]["字段完整度"] == "87.5%"
    assert summary["lead_grading"]["硬规则一致率"] == "96.67%"
    assert summary["deep_enrichment"]["无证据候选率"] == "0%"
    assert summary["lead_cleanup"]["错误合并建议数"] == "0"


def test_phase4_sample_metrics_file_matches_generated_content() -> None:
    report_path = Path(__file__).resolve().parents[3] / "docs" / "reports" / "phase-4" / "phase4-sample-metrics.md"
    expected = Phase4SampleMetricsService().render_markdown(
        metrics=Phase4SampleMetricsService.demo_metrics()
    )

    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == expected
