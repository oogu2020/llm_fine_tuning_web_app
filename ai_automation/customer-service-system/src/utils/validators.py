"""Input validation utilities."""

import re
from typing import Any

from pydantic import EmailStr, ValidationError


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_non_empty(value: Any, field_name: str) -> None:
    """Validate that a value is not empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{field_name} cannot be empty")


def validate_subject(subject: str, max_length: int = 500) -> str:
    """Validate and clean email subject."""
    if not subject or not subject.strip():
        return "No Subject"

    subject = subject.strip()

    if len(subject) > max_length:
        subject = subject[:max_length]

    # Remove control characters
    subject = "".join(char for char in subject if ord(char) >= 32)

    return subject


def validate_confidence_score(score: float) -> float:
    """Validate confidence score is between 0 and 1."""
    if not 0.0 <= score <= 1.0:
        raise ValueError("Confidence score must be between 0.0 and 1.0")
    return score


def sanitize_string(value: str) -> str:
    """Sanitize string input."""
    # Remove null bytes
    value = value.replace("\x00", "")
    # Strip whitespace
    value = value.strip()
    return value
