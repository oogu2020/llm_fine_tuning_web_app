# Testing Guide

## Quick Start

### 1. Run Unit Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_agent.py
pytest tests/test_services.py
pytest tests/test_integration.py

# Run with verbose output
pytest -v
```

### 2. Manual Testing (No API Keys Needed)

```bash
# Run the manual test script with mocked services
python tests/manual_test.py
```

This tests the workflow logic without requiring:
- Anthropic/OpenAI API keys
- Email servers
- ChromaDB setup

### 3. Test with Real Services

#### Configure Environment

```bash
# Copy and edit .env
cp .env.example .env

# Add your API keys
ANTHROPIC_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here
```

#### Test LLM Service

```python
# Python console
from src.services.llm_service import get_llm_service

llm = get_llm_service()
client = llm.get_client()
print("LLM client initialized:", type(client))
```

#### Test Knowledge Base

```bash
# Index sample documents
python -m src.cli index-docs

# Search the KB
python -m src.cli search-kb
```

#### Test Single Email Processing

```bash
# Process a test email manually
python -m src.cli process

# You'll be prompted for:
# - Subject: How do I reset my password?
# - Body: I forgot my password...
# - Customer email: test@example.com
```

#### Test API Server

```bash
# Start the server
python -m src.cli serve

# In another terminal, test the API:
curl -X POST http://localhost:8000/api/v1/emails/process \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "How do I reset my password?",
    "body": "I forgot my password and can'\''t log in.",
    "sender": "customer@example.com"
  }'
```

### 4. Test Email Fetching (Requires IMAP)

```bash
# Configure email in .env first
EMAIL_HOST=imap.gmail.com
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Fetch unread emails
python -m src.cli fetch
```

**Note**: For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

## Test Scenarios

### Scenario 1: Password Reset (Should Auto-Respond)

**Input**: "How do I reset my password?"

**Expected Flow**:
1. ✓ Classified as `account_issue`
2. ✓ Retrieves FAQ about password reset
3. ✓ Drafts helpful response
4. ✓ Review approves
5. ✓ Email sent

### Scenario 2: Billing Question (Should Auto-Respond)

**Input**: "I want to cancel my subscription"

**Expected Flow**:
1. ✓ Classified as `billing`
2. ✓ Retrieves billing policy
3. ✓ Drafts response with cancellation steps
4. ✓ Review approves
5. ✓ Email sent

### Scenario 3: Angry Complaint (Should Escalate)

**Input**: "I'm furious! Your service is terrible!"

**Expected Flow**:
1. ✓ Classified as `complaint`
2. ✓ High priority detected
3. ✓ `requires_escalation: true`
4. ✓ Routed to human agent
5. ✓ Email status: `escalated`

### Scenario 4: Unknown Question (Should Retry)

**Input**: "Do you support Martian time zones?"

**Expected Flow**:
1. ✓ Classified as `general_inquiry` (low confidence)
2. ✓ Retrieves docs (limited results)
3. ✓ Drafts response
4. ✓ Review may reject (low confidence)
5. ✓ Retries drafting (max 5 times)
6. ✓ Eventually escalates if quality too low

## Writing Tests

### Unit Test Template

```python
# tests/test_my_feature.py
import pytest
from src.agent.graph import my_node
from src.schemas.agent import AgentState

def test_my_node_success():
    """Test my_node with valid input."""
    state: AgentState = {
        "email": create_test_email(),
        # ... other required fields
    }

    result = my_node(state)

    assert result["some_field"] == expected_value
    assert len(result["errors"]) == 0

def test_my_node_handles_errors():
    """Test my_node error handling."""
    state: AgentState = {
        # Missing required fields
    }

    result = my_node(state)

    assert len(result["errors"]) == 1
```

### Mocking External Services

```python
from unittest.mock import MagicMock, patch

@patch("src.agent.graph.get_llm_service")
def test_with_mock_llm(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"intent": "test"}'
    mock_get_llm.return_value = mock_llm

    # Your test code here
```

## Debugging

### Enable Debug Logging

```python
# In your test or script
import logging
logging.getLogger("customer_support_agent").setLevel(logging.DEBUG)
```

Or set in `.env`:
```
LOG_LEVEL=DEBUG
```

### Visualize Graph

```python
from src.agent.graph import support_agent

# Generate Mermaid diagram
print(support_agent.get_graph().draw_mermaid())

# Or save as PNG (requires graphviz)
support_agent.get_graph().draw_png("workflow.png")
```

### Step Through Workflow

```python
from src.agent.graph import (
    ingest_node, classify_node, retrieve_node,
    draft_node, review_node, send_node
)

# Test individual nodes
state = {"email": test_email}
state = ingest_node(state)
state = classify_node(state)
# ... etc
```

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'src'`

**Solution**: Run from project root with:
```bash
python -m pytest tests/
```

### Issue: LLM returns invalid JSON

**Check**: The agent handles this by trying to extract JSON from markdown or falling back to defaults. Check logs for warnings.

### Issue: ChromaDB connection errors

**Solution**: Ensure the `data/chroma` directory exists and is writable:
```bash
mkdir -p data/chroma
```

### Issue: Email authentication fails

**Solution**: For Gmail, use an App Password, not your regular password. Enable 2FA first.

## Continuous Integration

Example GitHub Actions workflow (`.github/workflows/test.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov

    - name: Run tests
      run: pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```
