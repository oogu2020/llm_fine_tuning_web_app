"""Tests for the LangGraph agent workflow."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.agent.graph import (
    classify_node,
    draft_node,
    escalate_node,
    ingest_node,
    retrieve_node,
    review_node,
    route_after_classify,
    route_after_review,
    send_node,
)
from src.schemas.agent import AgentState, AgentStep, RetrievalResult
from src.schemas.email import (
    CustomerEmail,
    EmailClassification,
    EmailContent,
    EmailMetadata,
    EmailResponse,
    EmailStatus,
    IntentCategory,
    Priority,
)


@pytest.fixture
def sample_email():
    """Create a sample customer email."""
    return CustomerEmail(
        id="test-123",
        metadata=EmailMetadata(
            message_id="msg-123",
            subject="How do I reset my password?",
            sender="customer@example.com",
            sender_name="John Doe",
            to=["support@company.com"],
            received_at=datetime.utcnow(),
        ),
        content=EmailContent(
            body_text="I forgot my password and can't log in. Please help!",
        ),
    )


@pytest.fixture
def sample_classification():
    """Create a sample classification."""
    return EmailClassification(
        intent=IntentCategory.ACCOUNT_ISSUE,
        priority=Priority.HIGH,
        confidence=0.9,
        requires_escalation=False,
        key_points=["Forgot password", "Cannot log in"],
    )


@pytest.fixture
def sample_retrieved_docs():
    """Create sample retrieved documents."""
    return [
        RetrievalResult(
            content="To reset your password, click 'Forgot Password' on the login page.",
            source="faq.md",
            similarity_score=0.95,
        ),
        RetrievalResult(
            content="Password reset links expire after 24 hours.",
            source="policies.md",
            similarity_score=0.85,
        ),
    ]


class TestIngestNode:
    """Tests for the ingest node."""

    def test_ingest_node_processes_email(self, sample_email):
        """Test that ingest node processes email correctly."""
        state: AgentState = {"email": sample_email}

        result = ingest_node(state)

        assert result["current_step"] == AgentStep.CLASSIFY
        assert result["email"].status == EmailStatus.CLASSIFIED

    def test_ingest_node_handles_missing_email(self):
        """Test that ingest node handles missing email."""
        state: AgentState = {}

        result = ingest_node(state)

        assert len(result["errors"]) == 1
        assert result["errors"][0].step == AgentStep.INGEST


class TestClassifyNode:
    """Tests for the classify node."""

    @patch("src.agent.graph.get_llm_service")
    @patch("src.agent.graph.load_prompt")
    def test_classify_node_success(
        self, mock_load_prompt, mock_get_llm, sample_email
    ):
        """Test successful classification."""
        mock_load_prompt.return_value = "classify prompt"

        mock_llm = MagicMock()
        mock_llm.generate.return_value = json.dumps({
            "intent": "account_issue",
            "priority": "high",
            "confidence": 0.9,
            "requires_escalation": False,
            "key_points": ["password reset"],
        })
        mock_get_llm.return_value = mock_llm

        state: AgentState = {"email": sample_email}

        # Mock asyncio.run for async function
        import asyncio

        async def mock_generate(*args, **kwargs):
            return json.dumps({
                "intent": "account_issue",
                "priority": "high",
                "confidence": 0.9,
                "requires_escalation": False,
                "key_points": ["password reset"],
            })

        mock_llm.generate = mock_generate

        result = classify_node(state)

        assert result["classification"] is not None
        assert result["email"].classification is not None

    @patch("src.agent.graph.get_llm_service")
    def test_classify_node_json_parse_error(self, mock_get_llm, sample_email):
        """Test handling of invalid JSON response."""
        import asyncio

        async def mock_generate(*args, **kwargs):
            return "Invalid JSON"

        mock_llm = MagicMock()
        mock_llm.generate = mock_generate
        mock_get_llm.return_value = mock_llm

        state: AgentState = {"email": sample_email}
        result = classify_node(state)

        assert len(result["errors"]) == 1


class TestRetrieveNode:
    """Tests for the retrieve node."""

    @patch("src.agent.graph.get_kb_service")
    def test_retrieve_node_success(
        self, mock_get_kb, sample_email, sample_classification
    ):
        """Test successful document retrieval."""
        mock_kb = MagicMock()
        mock_kb.search.return_value = [
            RetrievalResult(
                content="Test doc",
                source="test.md",
                similarity_score=0.9,
            )
        ]
        mock_get_kb.return_value = mock_kb

        state: AgentState = {
            "email": sample_email,
            "classification": sample_classification,
        }

        result = retrieve_node(state)

        assert len(result["retrieved_documents"]) > 0
        mock_kb.search.assert_called_once()

    def test_retrieve_node_missing_classification(self, sample_email):
        """Test retrieval without classification."""
        state: AgentState = {"email": sample_email}

        result = retrieve_node(state)

        assert len(result["errors"]) == 1


class TestDraftNode:
    """Tests for the draft node."""

    @patch("src.agent.graph.get_llm_service")
    @patch("src.agent.graph.load_prompt")
    def test_draft_node_success(
        self,
        mock_load_prompt,
        mock_get_llm,
        sample_email,
        sample_classification,
        sample_retrieved_docs,
    ):
        """Test successful response drafting."""
        mock_load_prompt.return_value = "draft prompt"

        import asyncio

        async def mock_generate(*args, **kwargs):
            return json.dumps({
                "subject": "Re: How do I reset my password?",
                "body": "Here's how to reset your password...",
                "tone": "professional",
                "citations": ["faq.md"],
                "confidence": 0.88,
            })

        mock_llm = MagicMock()
        mock_llm.generate = mock_generate
        mock_get_llm.return_value = mock_llm

        state: AgentState = {
            "email": sample_email,
            "classification": sample_classification,
            "retrieved_documents": sample_retrieved_docs,
        }

        result = draft_node(state)

        assert result["draft_response"] is not None
        assert result["email"].response is not None
        assert result["email"].status == EmailStatus.REVIEWING


class TestReviewNode:
    """Tests for the review node."""

    @patch("src.agent.graph.get_llm_service")
    @patch("src.agent.graph.load_prompt")
    def test_review_node_approves(
        self,
        mock_load_prompt,
        mock_get_llm,
        sample_email,
        sample_classification,
        sample_retrieved_docs,
    ):
        """Test review node approves good response."""
        mock_load_prompt.return_value = "review prompt"

        import asyncio

        async def mock_generate(*args, **kwargs):
            return json.dumps({
                "approved": True,
                "score": 0.92,
                "issues": [],
                "feedback": "",
            })

        mock_llm = MagicMock()
        mock_llm.generate = mock_generate
        mock_get_llm.return_value = mock_llm

        sample_email.response = EmailResponse(
            subject="Re: Test",
            body="Test response",
            confidence=0.9,
        )

        state: AgentState = {
            "email": sample_email,
            "classification": sample_classification,
            "retrieved_documents": sample_retrieved_docs,
            "draft_response": sample_email.response,
            "iteration_count": 0,
        }

        result = review_node(state)

        assert result["review_result"]["approved"] is True
        assert result["iteration_count"] == 1

    @patch("src.agent.graph.get_llm_service")
    @patch("src.agent.graph.load_prompt")
    def test_review_node_rejects(
        self, mock_load_prompt, mock_get_llm, sample_email, sample_classification
    ):
        """Test review node rejects poor response."""
        mock_load_prompt.return_value = "review prompt"

        import asyncio

        async def mock_generate(*args, **kwargs):
            return json.dumps({
                "approved": False,
                "score": 0.5,
                "issues": ["Missing information"],
                "feedback": "Add more details",
            })

        mock_llm = MagicMock()
        mock_llm.generate = mock_generate
        mock_get_llm.return_value = mock_llm

        sample_email.response = EmailResponse(
            subject="Re: Test",
            body="Test response",
            confidence=0.5,
        )

        state: AgentState = {
            "email": sample_email,
            "classification": sample_classification,
            "retrieved_documents": [],
            "draft_response": sample_email.response,
            "iteration_count": 0,
        }

        result = review_node(state)

        assert result["review_result"]["approved"] is False
        assert result["review_result"]["feedback"] == "Add more details"


class TestSendNode:
    """Tests for the send node."""

    @patch("src.agent.graph.get_email_service")
    def test_send_node_auto_send_disabled(self, mock_get_email, sample_email):
        """Test send node when auto-send is disabled."""
        from src.core.config import settings

        settings.agent.auto_send = False

        sample_email.response = EmailResponse(
            subject="Re: Test",
            body="Test response",
        )

        state: AgentState = {
            "email": sample_email,
            "draft_response": sample_email.response,
        }

        result = send_node(state)

        assert result["status"] == EmailStatus.PENDING
        mock_get_email.return_value.send_response.assert_not_called()

    @patch("src.agent.graph.get_email_service")
    def test_send_node_sends_email(self, mock_get_email, sample_email):
        """Test send node sends email when approved."""
        from src.core.config import settings

        settings.agent.auto_send = True

        mock_email_service = MagicMock()
        mock_email_service.send_response.return_value = True
        mock_get_email.return_value = mock_email_service

        sample_email.response = EmailResponse(
            subject="Re: Test",
            body="Test response",
        )

        state: AgentState = {
            "email": sample_email,
            "draft_response": sample_email.response,
        }

        result = send_node(state)

        assert result["status"] == EmailStatus.SENT
        mock_email_service.send_response.assert_called_once()


class TestEscalateNode:
    """Tests for the escalate node."""

    def test_escalate_node_updates_status(self, sample_email):
        """Test escalation updates email status."""
        state: AgentState = {
            "email": sample_email,
            "errors": [],
        }

        result = escalate_node(state)

        assert result["email"].status == EmailStatus.ESCALATED
        assert result["status"] == EmailStatus.ESCALATED


class TestRouting:
    """Tests for conditional routing."""

    def test_route_after_classify_escalates_when_required(self, sample_classification):
        """Test routing escalates when classification requires it."""
        sample_classification.requires_escalation = True

        state: AgentState = {
            "classification": sample_classification,
            "errors": [],
        }

        result = route_after_classify(state)

        assert result == AgentStep.ESCALATE

    def test_route_after_classify_retrieves_when_confident(self, sample_classification):
        """Test routing retrieves when classification is confident."""
        sample_classification.requires_escalation = False

        state: AgentState = {
            "classification": sample_classification,
            "errors": [],
        }

        result = route_after_classify(state)

        assert result == AgentStep.RETRIEVE

    def test_route_after_review_sends_when_approved(self):
        """Test routing sends when review approves."""
        state: AgentState = {
            "review_result": {"approved": True},
            "iteration_count": 1,
        }

        result = route_after_review(state)

        assert result == AgentStep.SEND

    def test_route_after_review_revises_when_rejected(self):
        """Test routing revises when review rejects."""
        state: AgentState = {
            "review_result": {"approved": False},
            "iteration_count": 1,
            "max_iterations": 5,
        }

        result = route_after_review(state)

        assert result == AgentStep.DRAFT

    def test_route_after_review_escalates_at_max_iterations(self):
        """Test routing escalates when max iterations reached."""
        state: AgentState = {
            "review_result": {"approved": False},
            "iteration_count": 5,
            "max_iterations": 5,
        }

        result = route_after_review(state)

        assert result == AgentStep.ESCALATE
