"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path

# Ensure src is in path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Provide test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_email_data():
    """Sample email data for tests."""
    return {
        "subject": "Test Support Request",
        "body": "I need help with my account login.",
        "sender": "customer@example.com",
        "sender_name": "John Doe",
    }
