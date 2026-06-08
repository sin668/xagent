from pathlib import Path

from app.services.error_classification import (
    FailedCaseClassificationService,
    is_non_retryable_compliance_error,
)


def test_failed_case_classification_covers_required_error_groups() -> None:
    service = FailedCaseClassificationService()
    cases = service.demo_failed_cases()
    summary = service.summarize(cases)

    assert summary["case_count"] >= 6
    assert summary["agent_types"] == [
        "Deep Enrichment",
        "Lead Cleanup",
        "Lead Extraction",
        "Lead Grading",
        "Source Discovery",
    ]
    assert summary["non_retryable_count"] >= 4
    assert summary["retryable_count"] >= 1
    assert "schema_validation_error" in summary["error_types"]
    assert "evidence_validation_error" in summary["error_types"]
    assert "forbidden_source_error" in summary["error_types"]
    assert "hard_rule_conflict" in summary["error_types"]


def test_compliance_hard_rule_failures_are_not_retryable() -> None:
    for error_type in (
        "schema_validation_error",
        "evidence_validation_error",
        "forbidden_source_error",
        "hard_rule_conflict",
        "risk_blocked",
        "contract_mismatch",
    ):
        assert is_non_retryable_compliance_error(error_type) is True

    for case in FailedCaseClassificationService.demo_failed_cases():
        if case.error_type in {"forbidden_source_error", "hard_rule_conflict", "risk_blocked"}:
            assert case.retryable is False
            assert "不可自动重试" in case.recommendation


def test_failed_cases_report_renders_classification_and_recommendations() -> None:
    report = FailedCaseClassificationService.render_markdown(
        cases=FailedCaseClassificationService.demo_failed_cases()
    )

    assert "# 第四阶段失败案例与不可重试错误整理" in report
    assert "按 Agent 类型、错误类型、是否可重试分类" in report
    assert "schema 不满足" in report
    assert "证据缺失" in report
    assert "Forbidden 来源" in report
    assert "硬规则冲突" in report
    assert "合规硬规则失败不得归类为可自动重试成功的问题" in report
    assert "不自动修改历史 run 状态" in report
    assert "不自动重跑失败任务" in report
    assert "不输出最终 Go/No-Go 结论" in report


def test_failed_cases_report_file_matches_generated_content() -> None:
    report_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "reports"
        / "phase-4"
        / "failed-cases-and-non-retryable-errors.md"
    )
    expected = FailedCaseClassificationService.render_markdown(
        cases=FailedCaseClassificationService.demo_failed_cases()
    )

    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == expected
