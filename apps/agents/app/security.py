from hmac import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.settings import get_settings


API_KEY_HEADER = "X-Agents-Api-Key"
API_KEY_ERROR = "Invalid or missing agents API key"


def require_internal_api_key(
    agents_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> None:
    expected_api_key = get_settings().agents_api_key
    if not expected_api_key or not agents_api_key or not compare_digest(agents_api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=API_KEY_ERROR,
        )
