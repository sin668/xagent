from contextlib import asynccontextmanager
import logging
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.channel_discovery import router as channel_discovery_router
from app.api.channel_risk import router as channel_risk_router
from app.api.channel_plans import router as channel_plans_router
from app.api.compliance import router as compliance_router
from app.api.customers import router as customers_router
from app.api.customer_followups import router as customer_followups_router
from app.api.customer_vehicle_intents import router as customer_vehicle_intents_router
from app.api.dashboard import router as dashboard_router
from app.api.failed_cases import router as failed_cases_router
from app.api.inventory import router as inventory_router
from app.api.knowledge import router as knowledge_router
from app.api.lead_enrichment import field_candidate_router as lead_enrichment_field_candidate_router
from app.api.lead_enrichment import router as lead_enrichment_router
from app.api.lead_cleanup import router as lead_cleanup_router
from app.api.lead_extraction_from_sources import router as lead_extraction_from_sources_router
from app.api.lead_source_candidates import router as lead_source_candidates_router
from app.api.llm_health import router as llm_health_router
from app.api.llm_lead_extraction import router as llm_lead_extraction_router
from app.api.llm_lead_grading import router as llm_lead_grading_router
from app.api.llm_prompt_templates import router as llm_prompt_templates_router
from app.api.outreach_drafts import router as outreach_drafts_router
from app.api.phase2_dashboard import router as phase2_dashboard_router
from app.api.phase3_dashboard import router as phase3_dashboard_router
from app.api.public_page_read import router as public_page_read_router
from app.api.raw_collection import router as raw_collection_router
from app.api.risk_events import router as risk_events_router
from app.api.source_discovery_agent import router as source_discovery_agent_router
from app.api.staging_leads import router as staging_leads_router
from app.api.sync import router as sync_router
from app.services.agent_scheduler_bootstrap import shutdown_agent_scheduler, start_agent_scheduler
from app.services.agent_thread_runner import AgentThreadRunner
from app.settings import settings


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_scheduler = start_agent_scheduler()
    app.state.agent_scheduler = agent_scheduler
    try:
        yield
    finally:
        AgentThreadRunner.shutdown(wait=True)
        shutdown_agent_scheduler(agent_scheduler)


app = FastAPI(title="Overseas Vehicle Leads AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(channel_discovery_router)
app.include_router(channel_risk_router)
app.include_router(channel_plans_router)
app.include_router(compliance_router)
app.include_router(customers_router)
app.include_router(customer_followups_router)
app.include_router(customer_vehicle_intents_router)
app.include_router(dashboard_router)
app.include_router(failed_cases_router)
app.include_router(inventory_router)
app.include_router(knowledge_router)
app.include_router(lead_enrichment_field_candidate_router)
app.include_router(lead_enrichment_router)
app.include_router(lead_cleanup_router)
app.include_router(lead_extraction_from_sources_router)
app.include_router(lead_source_candidates_router)
app.include_router(llm_health_router)
app.include_router(llm_lead_extraction_router)
app.include_router(llm_lead_grading_router)
app.include_router(llm_prompt_templates_router)
app.include_router(outreach_drafts_router)
app.include_router(phase2_dashboard_router)
app.include_router(phase3_dashboard_router)
app.include_router(public_page_read_router)
app.include_router(raw_collection_router)
app.include_router(risk_events_router)
app.include_router(source_discovery_agent_router)
app.include_router(staging_leads_router)
app.include_router(sync_router)


@app.middleware("http")
async def log_request_duration(request, call_next):
    started_at = perf_counter()
    response = await call_next(request)
    duration_ms = (perf_counter() - started_at) * 1000
    log = logger.warning if duration_ms >= 1000 else logger.info
    log(
        "API 请求耗时：method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "vehicle-leads-api"}
