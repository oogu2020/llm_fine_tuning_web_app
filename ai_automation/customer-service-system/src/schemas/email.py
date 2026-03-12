"""Pydantic schemas for email data."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class EmailStatus(str, Enum):
    """Email processing status."""

    PENDING = "pending"
    CLASSIFIED = "classified"
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    SENT = "sent"
    ESCALATED = "escalated"
    FAILED = "failed"


class IntentCategory(str, Enum):
    """Customer intent categories."""

    GENERAL_INQUIRY = "general_inquiry"
    TECHNICAL_SUPPORT = "technical_support"
    BILLING = "billing"
    REFUND_REQUEST = "refund_request"
    ACCOUNT_ISSUE = "account_issue"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    SPAM = "spam"
    UNKNOWN = "unknown"


class Priority(str, Enum):
    """Ticket priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmailMetadata(BaseModel):
    """Email metadata from IMAP."""

    message_id: str
    thread_id: str | None = None
    received_at: datetime
    subject: str
    sender: EmailStr
    sender_name: str = ""
    to: list[EmailStr]
    cc: list[EmailStr] = []
    has_attachments: bool = False


class EmailContent(BaseModel):
    """Email body content."""

    body_text: str
    body_html: str | None = None
    stripped_signature: str | None = None


class EmailClassification(BaseModel):
    """Classification results from LLM."""

    intent: IntentCategory
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    requires_escalation: bool
    key_points: list[str] = []
    suggested_category: str | None = None


class EmailResponse(BaseModel):
    """Generated email response."""

    subject: str
    body: str
    body_html: str | None = None
    tone: Literal["professional", "friendly", "formal", "apologetic"] = "professional"
    citations: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0)


class CustomerEmail(BaseModel):
    """Complete customer email model."""

    id: str = Field(default_factory=lambda: "")
    metadata: EmailMetadata
    content: EmailContent
    classification: EmailClassification | None = None
    response: EmailResponse | None = None
    status: EmailStatus = EmailStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: dict[str, Any] = {}

    class Config:
        use_enum_values = True


class EmailCreateRequest(BaseModel):
    """Request to process a new email."""

    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    sender: EmailStr
    sender_name: str = ""


class EmailProcessResponse(BaseModel):
    """Response after processing an email."""

    email_id: str
    status: EmailStatus
    classification: EmailClassification | None = None
    response: EmailResponse | None = None
    message: str | None = None
