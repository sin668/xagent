from pathlib import Path

from app.services.phase4_go_no_go import Phase4GoNoGoReportService


def test_phase4_go_no_go_decisions_answer_required_questions() -> None:
    service = Phase4GoNoGoReportService()
    decisions = service.decisions()

    assert decisions["deep_enrichment"]["decision"] == "Go：继续小范围 active_run"
    assert decisions["lead_cleanup"]["decision"] == "Go：继续小范围 active_run"
    assert decisions["source_discovery"]["decision"] == "No-Go：保持 shadow_run"
    assert decisions["lead_extraction_grading"]["decision"] == "No-Go：保持 shadow_run"
    assert decisions["api_retry_worker"]["decision"] == "No-Go：下一阶段暂不开始废弃"


def test_phase4_go_no_go_report_renders_sources_risks_and_followups() -> None:
    report = Phase4GoNoGoReportService.render_markdown()

    assert "# 第四阶段 Go/No-Go 决策报告" in report
    assert "Deep Enrichment：Go，继续小范围 active_run" in report
    assert "Lead Cleanup：Go，继续小范围 active_run" in report
    assert "Source Discovery：No-Go，保持 shadow_run" in report
    assert "Lead Extraction/Grading：No-Go，保持 shadow_run" in report
    assert "`apps/api` retry worker：No-Go，下一阶段暂不开始废弃" in report
    assert "阻塞风险" in report
    assert "非阻塞风险" in report
    assert "后续 Epic/Story 建议" in report
    assert "不得执行生产切换" in report
    assert "不得删除 `apps/api` retry worker" in report
    assert "不得自动调整任何 Agent 开关" in report
    assert "docs/reports/phase-4/phase4-sample-metrics.md" in report
    assert "docs/reports/phase-4/failed-cases-and-non-retryable-errors.md" in report
    assert "两轮独立评审记录" in report


def test_phase4_go_no_go_report_file_matches_generated_content() -> None:
    report_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "reports"
        / "phase-4"
        / "phase4-go-no-go-report.md"
    )

    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == Phase4GoNoGoReportService.render_markdown()
