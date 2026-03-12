"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings
from src.core.logging import logger
from src.services.email_service import EmailService, get_email_service
from src.services.kb_service import KnowledgeBaseService, get_kb_service
from src.services.llm_service import LLMService, get_llm_service

# Security scheme
security = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    """Verify API key from Authorization header."""
    # For development, accept any key
    # In production, implement proper key validation
    if credentials:
        return credentials.credentials
    return "dev-key"


def get_llm() -> LLMService:
    """Dependency to get LLM service."""
    return get_llm_service()


def get_kb() -> KnowledgeBaseService:
    """Dependency to get KB service."""
    return get_kb_service()


def get_email() -> EmailService:
    """Dependency to get email service."""
    return get_email_service()
