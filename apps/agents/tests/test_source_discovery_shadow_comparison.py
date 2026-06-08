from app.services.source_discovery_comparison import SourceDiscoveryShadowComparisonService


def test_source_discovery_shadow_comparison_marks_added_missing_risk_and_evidence_differences() -> None:
    existing_results = [
        {
            "source_url": "https://dealer.example.ru/",
            "risk_level": "Low",
            "evidence_note": "Official dealer page with public stock.",
        },
        {
            "source_url": "https://directory.example.ru/autocity",
            "risk_level": "Medium",
            "evidence_note": "Directory lists address and contact.",
        },
        {
            "source_url": "https://legacy.example.ru/missing",
            "risk_level": "Low",
            "evidence_note": "Existing chain found this URL.",
        },
    ]
    shadow_output = {
        "schema_version": "phase4.agent.source_discovery.v1",
        "agent_mode": "shadow",
        "candidates": [
            {
                "url": "https://dealer.example.ru?utm_source=shadow",
                "normalized_url": "https://dealer.example.ru",
                "source_type": "official_website",
                "risk_level": "high",
                "evidence_summary": "Official dealer page with public stock.",
            },
            {
                "url": "https://new.example.ru",
                "normalized_url": "https://new.example.ru",
                "source_type": "official_website",
                "risk_level": "low",
                "evidence_summary": "New public dealer website with contact.",
            },
            {
                "url": "https://directory.example.ru/autocity",
                "normalized_url": "https://directory.example.ru/autocity",
                "source_type": "public_directory",
                "risk_level": "medium",
                "evidence_summary": "",
            },
        ],
        "blocked_items": [],
        "audit": {"writes_core_tables": False},
    }

    summary = SourceDiscoveryShadowComparisonService().compare(existing_results, shadow_output)

    assert summary["schema_version"] == "phase4.source_discovery.shadow_comparison.v1"
    assert summary["writes_business_tables"] is False
    assert summary["metrics"] == {
        "existing_count": 3,
        "shadow_count": 3,
        "matched_count": 2,
        "added_count": 1,
        "missing_count": 1,
        "risk_difference_count": 1,
        "evidence_difference_count": 1,
        "forbidden_leak_count": 0,
    }
    assert summary["added"] == [
        {
            "normalized_url": "https://new.example.ru",
            "shadow_url": "https://new.example.ru",
            "shadow_risk_level": "low",
        }
    ]
    assert summary["missing"] == [
        {
            "normalized_url": "https://legacy.example.ru/missing",
            "existing_url": "https://legacy.example.ru/missing",
            "existing_risk_level": "low",
        }
    ]
    assert summary["risk_differences"] == [
        {
            "normalized_url": "https://dealer.example.ru",
            "existing_risk_level": "low",
            "shadow_risk_level": "high",
        }
    ]
    assert summary["evidence_differences"] == [
        {
            "normalized_url": "https://directory.example.ru/autocity",
            "existing_has_evidence": True,
            "shadow_has_evidence": False,
        }
    ]


def test_source_discovery_shadow_comparison_flags_forbidden_leaks_as_blocking_risk() -> None:
    existing_results = [
        {
            "source_url": "https://dealer.example.ru",
            "risk_level": "Low",
            "evidence_note": "Official dealer page.",
        }
    ]
    shadow_output = {
        "schema_version": "phase4.agent.source_discovery.v1",
        "agent_mode": "shadow",
        "candidates": [
            {
                "url": "https://login.example.ru/private",
                "normalized_url": "https://login.example.ru/private",
                "source_type": "unknown",
                "risk_level": "forbidden",
                "evidence_summary": "login required",
            }
        ],
        "blocked_items": [],
        "audit": {"writes_core_tables": False},
    }

    summary = SourceDiscoveryShadowComparisonService().compare(existing_results, shadow_output)

    assert summary["metrics"]["forbidden_leak_count"] == 1
    assert summary["blocking_risks"] == [
        {
            "risk_type": "forbidden_leak",
            "normalized_url": "https://login.example.ru/private",
            "shadow_url": "https://login.example.ru/private",
            "message": "Forbidden 来源出现在 shadow 有效候选中，禁止进入 active_run。",
        }
    ]


def test_source_discovery_shadow_comparison_rejects_outputs_that_write_business_tables() -> None:
    shadow_output = {
        "schema_version": "phase4.agent.source_discovery.v1",
        "agent_mode": "shadow",
        "candidates": [],
        "blocked_items": [],
        "audit": {"writes_core_tables": True, "written_tables": ["lead_source_candidates"]},
    }

    try:
        SourceDiscoveryShadowComparisonService().compare([], shadow_output)
    except ValueError as exc:
        assert "shadow 对照不得写业务表" in str(exc)
    else:
        raise AssertionError("shadow 对照必须拒绝写业务表的输出")
