"""Graph contracts for the isolated phase 3 Agent runtime."""


def build_placeholder_graph() -> dict[str, object]:
    return {
        "name": "phase3_langgraph_placeholder",
        "runtime": "langgraph",
        "implemented": False,
        "writes_core_tables": False,
        "allowed_outputs": ["lead_enrichment_field_candidates", "lead_cleanup_suggestions"],
        "compliance_guards": [
            "no_auto_outreach",
            "no_auto_friend_request",
            "no_login_bulk_collection",
            "no_anti_scraping_bypass",
            "no_private_data_collection",
            "no_direct_core_writes",
            "api_service_validation_required",
            "human_review_required_for_key_actions",
        ],
    }
