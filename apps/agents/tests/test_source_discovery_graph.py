from app.graphs.source_discovery import (
    SOURCE_DISCOVERY_NODE_SEQUENCE,
    SourceDiscoveryGraphRunner,
    SourceDiscoveryGraphState,
)


class MockPublicSourceSearchTool:
    def search(self, queries):
        return [
            {
                "url": "https://dealer.example.ru",
                "title": "Auto City",
                "snippet": "Auto City sells used cars and posts public contact information.",
                "source_type": "official_website",
            },
            {
                "url": "https://dealer.example.ru/",
                "title": "Auto City duplicate",
                "snippet": "Duplicate URL should be deduped.",
                "source_type": "official_website",
            },
            {
                "url": "https://social.example.ru/autocity",
                "title": "Auto City social",
                "snippet": "Public social profile with used car posts.",
                "source_type": "public_social",
            },
            {
                "url": "https://login.example.ru/private",
                "title": "Login required",
                "snippet": "login required captcha",
                "source_type": "private_platform",
            },
        ]


class MockLLMDirectCandidatePlanner:
    last_audit = {
        "used": True,
        "queries": ["Russia public dealer directory"],
        "candidate_count": 1,
    }

    def plan(self, *, market, channel_strategy, fallback_queries):
        return {
            "queries": ["Russia public dealer directory"],
            "candidates": [
                {
                    "source_url": "https://directory.example.ru/dealers",
                    "platform": "Public directory",
                    "source_type": "public_directory",
                    "risk_level": "medium",
                    "discovery_reason": "公开目录可用于人工核验俄罗斯汽车经销商来源。",
                    "evidence_note": "公开目录入口，无需登录。",
                    "discovery_query": "Russia public dealer directory",
                }
            ],
        }


def test_source_discovery_graph_declares_required_node_sequence() -> None:
    assert SOURCE_DISCOVERY_NODE_SEQUENCE == (
        "load_channel_strategy",
        "build_discovery_queries",
        "search_public_sources",
        "normalize_source_candidates",
        "classify_channel_risk",
        "dedupe_candidates",
        "validate_source_evidence",
        "output_shadow_candidates",
    )


def test_source_discovery_graph_runner_uses_compiled_langgraph() -> None:
    runner = SourceDiscoveryGraphRunner(search_tool=MockPublicSourceSearchTool())

    assert runner.compiled_graph is not None


def test_source_discovery_graph_outputs_shadow_candidates_without_core_writes() -> None:
    runner = SourceDiscoveryGraphRunner(search_tool=MockPublicSourceSearchTool())
    state = SourceDiscoveryGraphState(
        discovery_run_id="11111111-1111-1111-1111-111111111111",
        market="Russia",
        channel_strategy={
            "target_segments": ["local_dealer"],
            "keywords": ["used cars", "Toyota dealer"],
            "allowed_source_types": ["official_website", "public_directory", "public_social"],
        },
        seed_urls=["https://dealer.example.ru"],
    )

    result = runner.run(state)

    assert result.output.schema_version == "phase4.agent.source_discovery.v1"
    assert result.output.discovery_run_id == "11111111-1111-1111-1111-111111111111"
    assert result.output.agent_mode == "shadow"
    assert result.executed_nodes == list(SOURCE_DISCOVERY_NODE_SEQUENCE)
    assert [item.url for item in result.output.candidates] == [
        "https://dealer.example.ru",
        "https://social.example.ru/autocity",
    ]
    official = result.output.candidates[0]
    assert official.source_type == "official_website"
    assert official.risk_level == "low"
    assert official.evidence_summary
    social = result.output.candidates[1]
    assert social.source_type == "public_social"
    assert social.risk_level == "high"
    assert social.review_status == "needs_manual_review"
    assert any(item["risk_level"] == "forbidden" for item in result.output.blocked_items)
    assert result.output.audit["writes_core_tables"] is False
    assert result.output.audit["output_table"] == "shadow_source_candidates"
    assert "lead_source_candidates" not in result.output.audit.get("written_tables", [])


def test_source_discovery_graph_accepts_llm_direct_candidates_without_seed_or_search_results() -> None:
    runner = SourceDiscoveryGraphRunner(llm_query_planner=MockLLMDirectCandidatePlanner())
    state = SourceDiscoveryGraphState(
        discovery_run_id="11111111-1111-1111-1111-111111111111",
        market="Russia",
        agent_mode="active",
        channel_strategy={
            "source": "default_source_discovery_agent",
            "keywords": ["автодилер"],
            "target_segments": ["dealer directories"],
        },
    )

    result = runner.run(state)

    assert [item.url for item in result.output.candidates] == ["https://directory.example.ru/dealers"]
    candidate = result.output.candidates[0]
    assert candidate.source_type == "public_directory"
    assert candidate.risk_level == "medium"
    assert candidate.evidence_summary == "公开目录入口，无需登录。"
    assert result.output.audit["llm_query_planner"]["candidate_count"] == 1
    assert result.output.audit["writes_core_tables"] is False


def test_source_discovery_graph_rejects_forbidden_private_collection_actions() -> None:
    runner = SourceDiscoveryGraphRunner(search_tool=MockPublicSourceSearchTool())
    state = SourceDiscoveryGraphState(
        discovery_run_id="11111111-1111-1111-1111-111111111111",
        market="Russia",
        agent_mode="active",
        channel_strategy={"keywords": ["used cars"]},
        requested_actions=["login_collect"],
    )

    try:
        runner.run(state)
    except ValueError as exc:
        assert "Source Discovery 不允许登录采集" in str(exc)
    else:
        raise AssertionError("Source Discovery graph must reject forbidden private collection actions")
