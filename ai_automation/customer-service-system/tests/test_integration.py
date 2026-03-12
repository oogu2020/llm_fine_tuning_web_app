"""Integration tests for the full agent workflow."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.agent.graph import create_support_agent_graph, support_agent
from src.schemas.agent import AgentState
from src.schemas.email import (
    CustomerEmail,
    EmailContent,
    EmailMetadata,
    EmailStatus,
)


@pytest.fixture
def complete_email():
    """Create a complete test email."""
    return CustomerEmail(
        id="int-test-123",
        metadata=EmailMetadata(
            message_id="msg-int-123",
            subject="I need help with my subscription",
            sender="customer@example.com",
            sender_name="Jane Doe",
            to=["support@company.com"],
            received_at=datetime.utcnow(),
        ),
        content=EmailContent(
            body_text="I want to cancel my subscription. How do I do that?",
        ),
    )


class TestFullWorkflow:
    """Integration tests for the complete agent workflow."""

    @patch("src.agent.graph.get_llm_service")
    @patch("src.agent.graph.get_kb_service")
    @patch("src.agent.graph.get_email_service")
    @patch("src.agent.graph.settings")
    def test_complete_workflow_success(
        self, mock_settings, mock_get_email, mock_get_kb, mock_get_llm, complete_email
    ):
        """Test a complete successful workflow from ingest to send."""
        # Mock settings
        mock_settings.agent.auto_send = True
        mock_settings.agent.max_iterations = 5

        # Mock LLM responses
        mock_llm = MagicMock()

        async def mock_generate(prompt):
            # Return different responses based on prompt content
            if "classify" in prompt.lower():
                return json.dumps({
                    "intent": "billing",
                    "priority": "medium",
                    "confidence": 0.92,
                    "requires_escalation": False,
                    "key_points": ["Cancel subscription"],
                })
            elif "draft" in prompt.lower():
                return json.dumps({
                    "subject": "Re: I need help with my subscription",
                    "body": "To cancel your subscription, go to Settings > Billing > Cancel Subscription.",
                    "tone": "professional",
                    "citations": ["faq.md"],
                    "confidence": 0.88,
                })
            elif "review" in prompt.lower():
                return json.dumps({
                    "approved": True,
                    "score": 0.90,
                    "issues": [],
                    "feedback": "",
                })
            return "{}"

        mock_llm.generate = mock_generate
        mock_get_llm.return_value = mock_llm

        # Mock KB service
        mock_kb = MagicMock()
        mock_kb.search.return_value = [
            MagicMock(
                content="To cancel, go to Settings > Billing > Cancel Subscription.",
                source="faq.md",
                similarity_score=0.95,
            )
        ]
        mock_get_kb.return_value = mock_kb

        # Mock email service
        mock_email_service = MagicMock()
        mock_email_service.send_response.return_value = True
        mock_get_email.return_value = mock_email_service

        # Create initial state
        initial_state: AgentState = {
            "email": complete_email,
            "current_step": None,
            "next_step": None,
            "classification": None,
            "retrieved_documents": [],
            "draft_response": None,
            "review_result": None,
            "iteration_count": 0,
            "max_iterations": 5,
            "status": EmailStatus.PENDING,
            "errors": [],
            "metadata": {},
        }

        # Run the graph
        final_state = support_agent.invoke(initial_state)

        # Assertions
        assert final_state["email"] is not None
        assert final_state["classification"] is not None
        assert final_state["draft_response"] is not None
        assert len(final_state["retrieved_documents"]) > 0

        # Verify email was sent
        mock_email_service.send_response.assert_called_once()

    @patch("src.agent.graph.get_llm_service")
    @patch("src.agent.graph.get_kb_service")
    def test_workflow_escalation(
        self, mock_get_kb, mock_get_llm, complete_email
    ):
        """Test workflow escalates for low confidence classification."""
        # Mock LLM to return low confidence
        mock_llm = MagicMock()

        async def mock_generate(prompt):
            if "classify" in prompt.lower():
                return json.dumps({
                    "intent": "complaint",
                    "priority": "high",
                    "confidence": 0.4,
                    "requires_escalation": True,
                    "key_points": ["Angry customer", "Unsatisfied"],
                })
            return "{}"

        mock_llm.generate = mock_generate
        mock_get_llm.return_value = mock_llm

        # Create initial state
        initial_state: AgentState = {
            "email": complete_email,
            "current_step": None,
            "next_step": None,
            "classification": None,
            "retrieved_documents": [],
            "draft_response": None,
            "review_result": None,
            "iteration_count": 0,
            "max_iterations": 5,
            "status": EmailStatus.PENDING,
            "errors": [],
            "metadata": {},
        }

        # Run the graph
        final_state = support_agent.invoke(initial_state)

        # Should have escalated
        assert final_state["email"].status == EmailStatus.ESCALATED

    @patch("src.agent.graph.get_llm_service")
    @patch("src.agent.graph.get_kb_service")
    def test_workflow_retry_drafting(
        self, mock_get_kb, mock_get_llm, complete_email
    ):
        """Test workflow retries drafting when review rejects."""
        call_count = {"review": 0}

        mock_llm = MagicMock()

        async def mock_generate(prompt):
            if "classify" in prompt.lower():
                return json.dumps({
                    "intent": "general_inquiry",
                    "priority": "low",
                    "confidence": 0.85,
                    "requires_escalation": False,
                    "key_points": ["Question"],
                })
            elif "draft" in prompt.lower():
                return json.dumps({
                    "subject": "Re: Question",
                    "body": "Here's the answer...",
                    "tone": "friendly",
                    "citations": [],
                    "confidence": 0.7,
                })
            elif "review" in prompt.lower():
                call_count["review"] += 1
                if call_count["review"] == 1:
                    # First review rejects
                    return json.dumps({
                        "approved": False,
                        "score": 0.6,
                        "issues": ["Need more detail"],
                        "feedback": "Add specific steps",
                    })
                else:
                    # Second review approves
                    return json.dumps({
                        "approved": True,
                        "score": 0.85,
                        "issues": [],
                        "feedback": "",
                    })
            return "{}"

        mock_llm.generate = mock_generate
        mock_get_llm.return_value = mock_llm

        mock_kb = MagicMock()
        mock_kb.search.return_value = []
        mock_get_kb.return_value = mock_kb

        initial_state: AgentState = {
            "email": complete_email,
            "current_step": None,
            "next_step": None,
            "classification": None,
            "retrieved_documents": [],
            "draft_response": None,
            "review_result": None,
            "iteration_count": 0,
            "max_iterations": 5,
            "status": EmailStatus.PENDING,
            "errors": [],
            "metadata": {},
        }

        with patch("src.agent.graph.settings") as mock_settings:
            mock_settings.agent.auto_send = False
            final_state = support_agent.invoke(initial_state)

        # Should have iterated twice
        assert final_state["iteration_count"] == 2


class TestWorkflowEdgeCases:
    """Test edge cases and error handling."""

    def test_workflow_handles_missing_email(self):
        """Test workflow handles missing email gracefully."""
        initial_state: AgentState = {
            "email": None,
            "errors": [],
        }

        from src.agent.graph import ingest_node
        result = ingest_node(initial_state)

        assert len(result["errors"]) == 1
        assert result["errors"][0].step.value == "ingest"

    def test_workflow_handles_empty_kb_results(self):
        """Test workflow handles empty knowledge base results."""
        email = CustomerEmail(
            id="test-empty",
            metadata=EmailMetadata(
                message_id="msg-empty",
                subject="Test",
                sender="test@test.com",
                sender_name="Test",
                to=["support@company.com"],
                received_at=datetime.utcnow(),
            ),
            content=EmailContent(body_text="Test question"),
        )

        with patch("src.agent.graph.get_kb_service") as mock_get_kb:
            mock_kb = MagicMock()
            mock_kb.search.return_value = []  # Empty results
            mock_get_kb.return_value = mock_kb

            from src.agent.graph import retrieve_node
            from src.schemas.email import EmailClassification, IntentCategory, Priority

            state: AgentState = {
                "email": email,
                "classification": EmailClassification(
                    intent=IntentCategory.GENERAL_INQUIRY,
                    priority=Priority.LOW,
                    confidence=0.8,
                    requires_escalation=False,
                    key_points=["test"],
                ),
            }

            result = retrieve_node(state)

            # Should still work with empty results
            assert result["retrieved_documents"] == []
