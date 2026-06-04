from pathlib import Path

from app.models.enums import PageSnapshotReadStatus
from app.services.raw_collection import RawCollectionService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0011_page_snapshots_source_evidence.py"


def test_page_snapshots_migration_declares_required_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0011"' in migration
    assert 'down_revision = "20260529_0010"' in migration
    assert '"page_snapshots"' in migration
    assert "candidate_url_id" in migration
    assert "page_title" in migration
    assert "text_excerpt" in migration
    assert "evidence_note" in migration
    assert "read_status" in migration
    assert "captured_at" in migration
    assert "robots_or_policy_note" in migration
    assert 'sa.ForeignKey("candidate_urls.id"' in migration


def test_page_snapshot_model_is_registered_for_alembic_metadata() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "PageSnapshot" in models_init
    assert "PageSnapshotReadStatus" in models_init


def test_page_snapshot_read_status_covers_required_values() -> None:
    assert PageSnapshotReadStatus.SUCCESS.value == "success"
    assert PageSnapshotReadStatus.BLOCKED.value == "blocked"
    assert PageSnapshotReadStatus.FAILED.value == "failed"
    assert PageSnapshotReadStatus.NEEDS_MANUAL_REVIEW.value == "needs_manual_review"


def test_page_snapshot_requires_candidate_url_id() -> None:
    try:
        RawCollectionService.validate_candidate_url_id(None)
    except ValueError as exc:
        assert "page snapshot 必须关联 candidate_url_id" in str(exc)
    else:
        raise AssertionError("page snapshot without candidate_url_id should be rejected")


def test_empty_evidence_note_is_allowed_in_raw_snapshot() -> None:
    assert RawCollectionService.normalize_evidence_note(None) == ""
    assert RawCollectionService.normalize_evidence_note("  ") == ""
    assert RawCollectionService.normalize_evidence_note(" 官网展示电话 ") == "官网展示电话"


def test_read_status_policy_wall_maps_to_needs_manual_review() -> None:
    assert RawCollectionService.normalize_read_status("captcha") == PageSnapshotReadStatus.NEEDS_MANUAL_REVIEW
    assert RawCollectionService.normalize_read_status("login_wall") == PageSnapshotReadStatus.NEEDS_MANUAL_REVIEW
    assert RawCollectionService.normalize_read_status("access_error") == PageSnapshotReadStatus.NEEDS_MANUAL_REVIEW
