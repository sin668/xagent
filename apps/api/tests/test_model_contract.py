from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]


def parse_class_file(relative_path: str) -> ast.Module:
    return ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))


def class_names(module: ast.Module) -> set[str]:
    return {node.name for node in module.body if isinstance(node, ast.ClassDef)}


def test_required_model_files_exist() -> None:
    expected = [
        "app/models/customer.py",
        "app/models/lead_source.py",
        "app/models/contact_method.py",
        "app/models/outreach_record.py",
        "app/models/inventory_item.py",
        "app/models/channel_risk_rule.py",
        "app/models/ai_audit_log.py",
        "app/models/compliance_review.py",
        "app/models/sync_log.py",
    ]
    for path in expected:
        assert (ROOT / path).exists(), path


def test_customer_model_has_required_story_fields() -> None:
    source = (ROOT / "app/models/customer.py").read_text(encoding="utf-8")
    for field in [
        "name",
        "country",
        "city",
        "customer_type",
        "grade",
        "status",
        "owner",
        "do_not_contact",
        "do_not_contact_reason",
    ]:
        assert field in source


def test_customer_has_one_to_many_relationships() -> None:
    source = (ROOT / "app/models/customer.py").read_text(encoding="utf-8")
    for relationship_name in ["sources", "contact_methods", "outreach_records", "ai_audit_logs", "compliance_reviews"]:
        assert relationship_name in source
        assert 'cascade="all, delete-orphan"' in source


def test_contact_method_supports_required_channels() -> None:
    source = (ROOT / "app/models/enums.py").read_text(encoding="utf-8")
    for value in ["EMAIL", "PHONE", "WHATSAPP", "TELEGRAM", "VKONTAKTE", "WEBSITE", "WEBSITE_FORM"]:
        assert value in source


def test_migration_uses_business_enum_values() -> None:
    migration = (ROOT / "alembic/versions/20260528_0001_initial_data_foundation.py").read_text(encoding="utf-8")
    for value in ['"Low"', '"Medium"', '"High"', '"Forbidden"', '"Invalid"', '"Watch"', '"telegram"', '"vkontakte"']:
        assert value in migration
    for technical_name in ['"LOW"', '"MEDIUM"', '"HIGH"', '"FORBIDDEN"', '"INVALID"', '"WATCH"', '"TELEGRAM"', '"VKONTAKTE"']:
        assert technical_name not in migration


def test_initial_migration_contains_required_tables() -> None:
    migration = (ROOT / "alembic/versions/20260528_0001_initial_data_foundation.py").read_text(encoding="utf-8")
    for table in [
        "customers",
        "lead_sources",
        "contact_methods",
        "outreach_records",
        "inventory_items",
        "channel_risk_rules",
        "ai_audit_logs",
        "compliance_reviews",
        "sync_logs",
    ]:
        assert f'"{table}"' in migration
