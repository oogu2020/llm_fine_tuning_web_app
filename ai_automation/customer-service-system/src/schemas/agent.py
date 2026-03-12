"""LangGraph state types and agent schemas."""

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from src.schemas.email import (
    CustomerEmail,
    EmailClassification,
    EmailResponse,
    EmailStatus,
)


class AgentStep(str, Enum):
    """Current step in the agent workflow."""

    INGEST = "ingest"
    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    DRAFT = "draft"
    REVIEW = "review"
    SEND = "send"
    ESCALATE = "escalate"
    END = "end"


class AgentError(BaseModel):
    """Error information for failed steps."""

    step: AgentStep
    message: str
    details: dict[str, Any] | None = None


class RetrievalResult(BaseModel):
    """Knowledge base retrieval result."""

    content: str
    source: str
    similarity_score: float


# =============================================================================
# LangGraph State (TypedDict)
# =============================================================================


def merge_dicts(left: dict, right: dict) -> dict:
    """Merge two dictionaries for reducer function."""
    result = left.copy()
    result.update(right)
    return result


def append_to_list(left: list, right: list) -> list:
    """Append items to list for reducer function."""
    return left + right


class AgentState(TypedDict, total=False):
    """LangGraph state definition for the support agent.

    This TypedDict defines the state passed between nodes in the graph.
    """

    # Core email data
    email: Annotated[CustomerEmail, lambda x, y: y or x]

    # Workflow step
    current_step: Annotated[AgentStep, lambda x, y: y or x]
    next_step: Annotated[AgentStep | None, lambda x, y: y or x]

    # Processing results
    classification: Annotated[EmailClassification | None, lambda x, y: y or x]
    retrieved_documents: Annotated[list[RetrievalResult], append_to_list]
    draft_response: Annotated[EmailResponse | None, lambda x, y: y or x]
    review_result: Annotated[dict | None, lambda x, y: y or x]

    # Iteration tracking
    iteration_count: Annotated[int, lambda x, y: x + (y or 0)]
    max_iterations: Annotated[int, lambda x, y: y or x]

    # Status and errors
    status: Annotated[EmailStatus, lambda x, y: y or x]
    errors: Annotated[list[AgentError], append_to_list]

    # Metadata
    metadata: Annotated[dict, merge_dicts]


class AgentConfig(BaseModel):
    """Configuration for the agent workflow."""

    max_iterations: int = Field(default=5, ge=1, le=10)
    escalation_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    auto_send: bool = False
    require_human_review: bool = True
    review_confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class WorkflowResult(BaseModel):
    """Final result of a workflow execution."""

    email_id: str
    success: bool
    final_status: EmailStatus
    steps_executed: list[AgentStep]
    errors: list[AgentError]
    duration_seconds: float
    email: CustomerEmail | None = None
