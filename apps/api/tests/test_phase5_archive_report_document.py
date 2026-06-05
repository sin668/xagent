from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "phase-5" / "phase5-execution-archive-report.md"
STORY_DIR = REPO_ROOT / "docs" / "stories" / "phase-5-small-run"


def test_phase5_archive_report_covers_all_stories_go_no_go_and_residual_risks() -> None:
    assert REPORT_PATH.exists(), "第五阶段归档报告必须落盘到 docs/reports/phase-5/"

    content = REPORT_PATH.read_text(encoding="utf-8")
    story_files = sorted(STORY_DIR.glob("P5-*.md"))

    assert len(story_files) == 48
    assert "第五阶段归档与执行报告" in content
    assert "真实 PostgreSQL/API/Redis" in content
    assert "Go/No-Go 结论" in content
    assert "pause_auto_send" in content
    assert "P5-E9-S4" in content and "phase5-e2e-integration-report" in content
    assert "未完成项与 owner" in content
    assert "残留风险" in content
    assert "下一阶段建议" in content
    assert "第一轮独立多维度评审" in content
    assert "第二轮独立多维度评审" in content

    missing_story_ids = [path.stem.split("-", maxsplit=3)[0:3] for path in story_files if path.stem not in content]
    assert not missing_story_ids, f"归档报告缺少 Story 条目：{missing_story_ids}"
