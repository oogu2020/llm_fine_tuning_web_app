"""General utility helpers."""

import re
import uuid
from datetime import datetime
from typing import Any


def generate_id() -> str:
    """Generate a unique ID for emails."""
    return str(uuid.uuid4())


def clean_email_body(text: str) -> str:
    """Clean email body by removing signatures and quoted replies."""
    # Remove common signature patterns
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        # Skip signature markers
        if re.match(r"^--\s*$", line.strip()):
            break
        # Skip quoted lines
        if line.strip().startswith(">"):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def format_timestamp(dt: datetime | None = None) -> str:
    """Format timestamp for logging."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat()


def mask_sensitive(data: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Mask sensitive values in a dictionary."""
    result = data.copy()
    for key in keys:
        if key in result and result[key]:
            result[key] = "***REDACTED***"
    return result


def extract_email_address(email_str: str) -> str:
    """Extract email from 'Name <email@domain.com>' format."""
    match = re.search(r"<([^>]+)>", email_str)
    if match:
        return match.group(1)
    return email_str.strip()


def safe_json_loads(data: Any) -> Any:
    """Safely parse JSON or return original data."""
    import json

    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    return data
