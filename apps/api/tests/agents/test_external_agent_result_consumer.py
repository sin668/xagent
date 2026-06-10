from copy import deepcopy
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.agent_task_run import AgentTaskRun
from app.models.candidate_url import CandidateUrl
from app.models.collection_task import CollectionTask
from app.models.lead_source_candidate import LeadSourceCandidate
from app.models.staging_lead import StagingLead
from app.services.external_agent_result_consumer import ExternalAgentResultConsumer


def make_session():
    engine = create_engine("sqlite:///:memory:")
    for model in (AgentTaskRun, LeadSourceCandidate, CollectionTask, CandidateUrl, StagingLead):
        model.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal()


def source_discovery_response() -> dict:
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": str(uuid4()),
        "request_id": str(uuid4()),
        "status": "succeeded",
        "agent_type": "source_discovery",
        "agent_mode": "shadow",
        "audit": {"writes_core_tables": False},
        "output": {
            "schema_version": "phase4.agent.source_discovery.v1",
            "discovery_run_id": str(uuid4()),
            "agent_mode": "shadow",
            "candidates": [
                {
                    "url": "https://dealer-shadow.example",
                    "normalized_url": "https://dealer-shadow.example/",
                    "source_type": "official_website",
                    "risk_level": "low",
                    "evidence_summary": "公开官网展示 used cars export 联系信息。",
                    "discovery_query": "Russia used cars dealer",
                    "review_status": "shadow_only",
                }
            ],
            "blocked_items": [],
            "audit": {"writes_core_tables": False, "market": "Russia"},
        },
    }


def lead_extraction_grading_response() -> dict:
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": str(uuid4()),
        "request_id": str(uuid4()),
        "status": "succeeded",
        "agent_type": "lead_extraction_grading",
        "agent_mode": "shadow",
        "audit": {"writes_core_tables": False},
        "output": {
            "schema_version": "phase4.agent.lead_extraction_grading.v1",
            "combined_run_id": str(uuid4()),
            "agent_mode": "shadow",
            "extraction": {
                "schema_version": "phase4.agent.lead_extraction.v1",
                "extraction_run_id": str(uuid4()),
                "agent_mode": "shadow",
                "candidates": [
                    {
                        "source_url": "https://lead-shadow.example",
                        "company_name": {
                            "field_name": "company_name",
                            "value": "Lead Shadow Motors",
                            "evidence": {"reference": "source_content", "quote": "Lead Shadow Motors exports vehicles."},
                        },
                        "email": {
                            "field_name": "email",
                            "value": "sales@lead-shadow.example",
                            "evidence": {"reference": "source_content", "quote": "sales@lead-shadow.example"},
                        },
                        "phone": {
                            "field_name": "phone",
                            "value": "+971 50 123 4567",
                            "evidence": {"reference": "source_content", "quote": "+971 50 123 4567"},
                        },
                        "country": {
                            "field_name": "country",
                            "value": "United Arab Emirates",
                            "evidence": {"reference": "source_content", "quote": "United Arab Emirates"},
                        },
                        "city": {
                            "field_name": "city",
                            "value": "Dubai",
                            "evidence": {"reference": "source_content", "quote": "Dubai"},
                        },
                        "vehicle_interest": {
                            "field_name": "vehicle_interest",
                            "value": "Toyota Land Cruiser",
                            "evidence": {"reference": "source_content", "quote": "Toyota Land Cruiser"},
                        },
                        "export_intent": {
                            "field_name": "export_intent",
                            "value": "exports vehicles",
                            "evidence": {"reference": "source_content", "quote": "exports vehicles"},
                        },
                        "website": {
                            "field_name": "website",
                            "value": "https://lead-shadow.example",
                            "evidence": {"reference": "source_url", "quote": "https://lead-shadow.example"},
                        },
                        "audit_status": "shadow_only",
                        "contacts": [
                            {
                                "contact_type": "email",
                                "value": "sales@lead-shadow.example",
                                "usage": "source_public_contact",
                                "evidence": {"reference": "source_content", "quote": "sales@lead-shadow.example"},
                            },
                            {
                                "contact_type": "email",
                                "value": "export@lead-shadow.example",
                                "usage": "source_public_contact",
                                "evidence": {"reference": "source_content", "quote": "export@lead-shadow.example"},
                            },
                            {
                                "contact_type": "phone",
                                "value": "+971 50 123 4567",
                                "usage": "source_public_contact",
                                "evidence": {"reference": "source_content", "quote": "+971 50 123 4567"},
                            },
                            {
                                "contact_type": "phone",
                                "value": "+971 50 765 4321",
                                "usage": "source_public_contact",
                                "evidence": {"reference": "source_content", "quote": "+971 50 765 4321"},
                            },
                        ],
                    }
                ],
                "validation_errors": [],
                "audit": {"writes_core_tables": False},
            },
            "grading": {
                "schema_version": "phase4.agent.lead_grading.v1",
                "grading_run_id": str(uuid4()),
                "agent_mode": "shadow",
                "suggestions": [
                    {
                        "source_url": "https://lead-shadow.example",
                        "recommended_grade": "A",
                        "status_route": "ready_for_manual_review",
                        "confidence_score": 0.92,
                        "reasons": ["联系方式完整", "出口意向明确"],
                        "triggered_rules": ["complete_contact"],
                        "explanations": {},
                        "auto_promote_customer": False,
                    }
                ],
                "audit": {"writes_core_tables": False},
            },
            "hard_rule_summary": {"hard_rules_applied": False, "triggered_rules": [], "risk_flags": []},
            "validation_summary": {
                "schema_passed": True,
                "schema_pass_rate": 1,
                "evidence_hit_rate": 1,
                "contact_anti_fabrication_passed": True,
                "contact_anti_fabrication_pass_rate": 1,
                "hard_rule_consistency_rate": 1,
                "invalid_contacts": [],
                "validation_errors": [],
            },
            "grade_delta_explanations": {},
            "audit": {"writes_core_tables": False},
        },
    }


def lead_extraction_grading_batch_response() -> dict:
    response = lead_extraction_grading_response()
    first_output = deepcopy(response["output"])
    second_output = deepcopy(response["output"])
    first_output["source_candidate_id"] = "candidate-1"
    second_output["source_candidate_id"] = "candidate-2"
    second_output["extraction"]["candidates"][0]["source_url"] = "https://lead-batch-second.example"
    second_output["extraction"]["candidates"][0]["company_name"]["value"] = "Second Batch Motors"
    second_output["extraction"]["candidates"][0]["company_name"]["evidence"]["quote"] = "Second Batch Motors exports vehicles."
    second_output["extraction"]["candidates"][0]["email"]["value"] = "sales@lead-batch-second.example"
    second_output["extraction"]["candidates"][0]["email"]["evidence"]["quote"] = "sales@lead-batch-second.example"
    second_output["grading"]["suggestions"][0]["source_url"] = "https://lead-batch-second.example"
    response["output"]["batch_results"] = [
        {
            "status": "succeeded",
            "source_candidate_id": "candidate-1",
            "source_url": "https://lead-shadow.example",
            "output": first_output,
        },
        {
            "status": "succeeded",
            "source_candidate_id": "candidate-2",
            "source_url": "https://lead-batch-second.example",
            "output": second_output,
        },
    ]
    return response


def test_consume_source_discovery_response_writes_lead_source_candidates() -> None:
    engine, session = make_session()
    try:
        result = ExternalAgentResultConsumer(session).consume_source_discovery_response(source_discovery_response())
        session.commit()

        candidates = list(session.scalars(select(LeadSourceCandidate)).all())
        assert result.summary["created_count"] == 1
        assert len(candidates) == 1
        assert candidates[0].source_url == "https://dealer-shadow.example"
        assert candidates[0].country == "Russia"
        assert candidates[0].approved_for_extraction is True
    finally:
        session.close()
        engine.dispose()


def test_consume_lead_extraction_grading_batch_response_writes_multiple_staging_leads() -> None:
    engine, session = make_session()
    try:
        result = ExternalAgentResultConsumer(session).consume_lead_extraction_grading_response(
            lead_extraction_grading_batch_response()
        )
        session.commit()

        leads = list(session.scalars(select(StagingLead)).all())
        assert result.summary["created_count"] == 2
        assert len(result.summary["processed_items"]) == 2
        assert len(leads) == 2
        assert {lead.customer_name for lead in leads} == {"Lead Shadow Motors", "Second Batch Motors"}
    finally:
        session.close()
        engine.dispose()


def test_consume_lead_extraction_grading_response_writes_staging_leads() -> None:
    engine, session = make_session()
    try:
        result = ExternalAgentResultConsumer(session).consume_lead_extraction_grading_response(lead_extraction_grading_response())
        session.commit()

        leads = list(session.scalars(select(StagingLead)).all())
        assert result.summary["created_count"] == 1
        assert len(leads) == 1
        assert leads[0].customer_name == "Lead Shadow Motors"
        assert leads[0].recommended_grade.value == "A"
        assert leads[0].contacts_json == [
            {"type": "email", "value": "sales@lead-shadow.example", "usage": "source_public_contact"},
            {"type": "email", "value": "export@lead-shadow.example", "usage": "source_public_contact"},
            {"type": "phone", "value": "+971 50 123 4567", "usage": "source_public_contact"},
            {"type": "phone", "value": "+971 50 765 4321", "usage": "source_public_contact"},
        ]
    finally:
        session.close()
        engine.dispose()
