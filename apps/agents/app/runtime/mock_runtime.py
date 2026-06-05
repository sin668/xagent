from __future__ import annotations

from typing import Any
from uuid import UUID

from app.graphs.deep_enrichment import DeepEnrichmentGraphRunner, DeepEnrichmentGraphState
from app.graphs.lead_cleanup import LeadCleanupGraphRunner, LeadCleanupGraphState


class MockAgentRuntime:
    def run_deep_enrichment(
        self,
        *,
        agent_run_id: UUID | str,
        staging_lead_id: UUID | str,
        lead_snapshot: dict[str, Any],
        missing_fields: list[str],
    ) -> dict:
        runner = DeepEnrichmentGraphRunner()
        result = runner.run(
            DeepEnrichmentGraphState(
                agent_run_id=agent_run_id,
                staging_lead_id=staging_lead_id,
                lead_snapshot=lead_snapshot,
                missing_fields=missing_fields,
            )
        )
        return result.output.model_dump(mode="json")

    def run_lead_cleanup(
        self,
        *,
        cleanup_run_id: UUID | str,
        leads: list[dict[str, Any]],
    ) -> dict:
        runner = LeadCleanupGraphRunner()
        result = runner.run(
            LeadCleanupGraphState(
                cleanup_run_id=cleanup_run_id,
                leads=leads,
            )
        )
        return result.output.model_dump(mode="json")
