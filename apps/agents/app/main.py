from fastapi import FastAPI

from app.api.agent_runs import router as agent_runs_router


SERVICE_NAME = "vehicle-leads-agents"
SERVICE_VERSION = "0.1.0"

app = FastAPI(
    title="Vehicle Leads Agents",
    version=SERVICE_VERSION,
)
app.include_router(agent_runs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }
