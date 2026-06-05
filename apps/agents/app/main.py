from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.agent_runs import router as agent_runs_router
from app.services.agent_logging import log_agent_auto_start_disabled, log_agent_service_start


SERVICE_NAME = "vehicle-leads-agents"
SERVICE_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_agent_service_start(service_name=SERVICE_NAME, service_version=SERVICE_VERSION)
    log_agent_auto_start_disabled()
    yield


app = FastAPI(
    title="Vehicle Leads Agents",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)
app.include_router(agent_runs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }
