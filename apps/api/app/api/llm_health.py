from fastapi import APIRouter

from app.settings import settings


router = APIRouter(prefix="/llm-health", tags=["llm-health"])


@router.get("")
def get_llm_health() -> dict[str, object]:
    api_key_configured = bool(settings.llm_api_key and settings.llm_api_key.get_secret_value())
    base_url_configured = bool(settings.llm_base_url)
    models = {
        "default": settings.llm_default_model,
        "source_discovery": settings.llm_source_discovery_model,
        "extraction": settings.llm_extraction_model,
        "grading": settings.llm_grading_model,
    }

    return {
        "provider": settings.llm_provider,
        "models": models,
        "base_url_configured": base_url_configured,
        "api_key_configured": api_key_configured,
        "configuration_complete": bool(
            settings.llm_provider
            and api_key_configured
            and base_url_configured
            and all(models.values())
        ),
    }
