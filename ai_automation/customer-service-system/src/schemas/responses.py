"""API response schemas."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Base API response wrapper."""

    success: bool = True
    data: T | None = None
    message: str | None = None
    error: str | None = None


class PaginatedResponse(BaseResponse[T]):
    """Paginated response wrapper."""

    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1)
    pages: int = Field(default=1, ge=1)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    agent_compiled: bool


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: str | None = None
    code: int = Field(default=500, ge=100, lt=600)
