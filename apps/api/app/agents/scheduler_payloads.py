from __future__ import annotations

from typing import Any


def build_external_source_discovery_input(*, request_id: str) -> dict[str, Any]:
    return {
        "discovery_run_id": request_id,
        "trigger_source": "scheduler_external_source_discovery",
        "market": "Russia",
        "channel_strategy": {
            "keywords": ["автодилер", "автосалон", "used cars", "import cars"],
            "target_segments": ["used car dealers", "vehicle import/export dealers"],
            "risk_policy": "仅允许公开来源 shadow_run；不得登录、私信、绕过反爬或自动写入业务表。",
        },
        "seed_urls": ["https://scheduler-shadow-source.example/dealers"],
        "requested_actions": [],
        "search_results": [],
    }


def build_external_lead_extraction_grading_input(*, request_id: str) -> dict[str, Any]:
    source_url = "https://scheduler-shadow-input.local/source"
    source_content = (
        "Scheduler Shadow Motors exports used Toyota Land Cruiser and Lexus LX vehicles to overseas buyers. "
        "Contact: sales@scheduler-shadow.example, +971 50 123 4567. "
        "Located in Dubai, United Arab Emirates. Website: https://scheduler-shadow.example. "
        "The company says it can arrange export documentation and shipping."
    )
    return {
        "combined_run_id": request_id,
        "extraction_run_id": request_id,
        "grading_run_id": request_id,
        "trigger_source": "scheduler_external_lead_extraction_grading",
        "source_url": source_url,
        "source_content": source_content,
        "risk_flags": [],
        "existing_grade": None,
        "expected_contacts": {
            "email": "sales@scheduler-shadow.example",
            "phone": "+971 50 123 4567",
        },
    }
