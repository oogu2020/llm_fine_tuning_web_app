#!/usr/bin/env python3
"""Manual testing script for the customer support agent.

Run this to test the agent without setting up email servers:
    python tests/manual_test.py

This script uses mock services so you can test the workflow logic
without API keys or external dependencies.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.agent.graph import support_agent
from src.schemas.agent import AgentState
from src.schemas.email import (
    CustomerEmail,
    EmailContent,
    EmailMetadata,
    EmailStatus,
)


def create_test_email(subject: str, body: str, sender: str = "customer@example.com"):
    """Create a test email."""
    return CustomerEmail(
        id=f"test-{hash(subject) % 10000}",
        metadata=EmailMetadata(
            message_id=f"msg-{hash(subject) % 10000}",
            subject=subject,
            sender=sender,
            sender_name="Test Customer",
            to=["support@company.com"],
            received_at=datetime.utcnow(),
        ),
        content=EmailContent(body_text=body),
    )


def run_test_scenario(name: str, email: CustomerEmail, expected_status: str):
    """Run a single test scenario."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Subject: {email.metadata.subject}")
    print(f"Body: {email.content.body_text[:100]}...")
    print()

    # Mock LLM responses
    def mock_llm_generate(prompt):
        import asyncio

        async def generate(*args, **kwargs):
            if "classify" in prompt.lower():
                # Classify based on content
                if "password" in email.content.body_text.lower():
                    return json.dumps({
                        "intent": "account_issue",
                        "priority": "high",
                        "confidence": 0.95,
                        "requires_escalation": False,
                        "key_points": ["Password reset request"],
                    })
                elif "cancel" in email.content.body_text.lower() or "refund" in email.content.body_text.lower():
                    return json.dumps({
                        "intent": "billing",
                        "priority": "high",
                        "confidence": 0.9,
                        "requires_escalation": False,
                        "key_points": ["Billing inquiry"],
                    })
                elif "angry" in email.content.body_text.lower() or "complaint" in email.content.body_text.lower():
                    return json.dumps({
                        "intent": "complaint",
                        "priority": "critical",
                        "confidence": 0.85,
                        "requires_escalation": True,
                        "key_points": ["Customer complaint"],
                    })
                else:
                    return json.dumps({
                        "intent": "general_inquiry",
                        "priority": "medium",
                        "confidence": 0.8,
                        "requires_escalation": False,
                        "key_points": ["General question"],
                    })
            elif "draft" in prompt.lower():
                return json.dumps({
                    "subject": f"Re: {email.metadata.subject}",
                    "body": f"Thank you for contacting us. Here's how we can help with your inquiry about: {email.content.body_text[:50]}...",
                    "tone": "professional",
                    "citations": ["faq.md"],
                    "confidence": 0.88,
                })
            elif "review" in prompt.lower():
                return json.dumps({
                    "approved": True,
                    "score": 0.9,
                    "issues": [],
                    "feedback": "",
                })
            return "{}"
        return generate()

    # Mock KB search
    def mock_kb_search(query, top_k=5):
        return [
            MagicMock(
                content="To reset your password, go to Settings > Password.",
                source="faq.md",
                similarity_score=0.95,
            ),
            MagicMock(
                content="To cancel subscription, go to Billing > Cancel.",
                source="policies.md",
                similarity_score=0.9,
            ),
        ]

    # Mock email sending
    def mock_send_email(*args, **kwargs):
        print(f"  📧 Would send email to: {kwargs.get('to_email', 'customer')}")
        print(f"     Subject: {kwargs.get('subject', 'N/A')}")
        return True

    # Apply mocks
    with patch("src.agent.graph.get_llm_service") as mock_llm_service, \
         patch("src.agent.graph.get_kb_service") as mock_kb_service, \
         patch("src.agent.graph.get_email_service") as mock_email_service, \
         patch("src.agent.graph.settings") as mock_settings:

        # Setup mocks
        mock_llm = MagicMock()
        mock_llm.generate = mock_llm_generate
        mock_llm_service.return_value = mock_llm

        mock_kb = MagicMock()
        mock_kb.search = mock_kb_search
        mock_kb_service.return_value = mock_kb

        mock_email = MagicMock()
        mock_email.send_response = mock_send_email
        mock_email_service.return_value = mock_email

        # Configure settings
        mock_settings.agent.auto_send = True
        mock_settings.agent.max_iterations = 5

        # Create initial state
        initial_state: AgentState = {
            "email": email,
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

        # Run the agent
        final_state = support_agent.invoke(initial_state)

        # Print results
        print(f"\n📊 RESULTS:")
        print(f"  Final Status: {final_state.get('status', 'N/A')}")
        print(f"  Iterations: {final_state.get('iteration_count', 0)}")

        if final_state.get("classification"):
            cls = final_state["classification"]
            print(f"  Intent: {cls.intent.value}")
            print(f"  Priority: {cls.priority.value}")
            print(f"  Confidence: {cls.confidence:.2f}")

        if final_state.get("draft_response"):
            response = final_state["draft_response"]
            print(f"\n  📝 Drafted Response:")
            print(f"     Subject: {response.subject}")
            print(f"     Body: {response.body[:200]}...")

        if final_state.get("errors"):
            print(f"\n  ⚠️  Errors: {len(final_state['errors'])}")
            for error in final_state["errors"]:
                print(f"     - {error.step}: {error.message}")

        # Verify result
        actual_status = final_state.get("status", EmailStatus.FAILED)
        if actual_status.value == expected_status:
            print(f"\n  ✅ PASS: Expected {expected_status}, got {actual_status.value}")
            return True
        else:
            print(f"\n  ❌ FAIL: Expected {expected_status}, got {actual_status.value}")
            return False


def main():
    """Run all test scenarios."""
    print("🚀 Customer Support Agent - Manual Test Suite")
    print("=" * 60)

    test_cases = [
        (
            "Password Reset Request",
            create_test_email(
                "How do I reset my password?",
                "I forgot my password and can't log in. Please help me reset it.",
            ),
            "sent",
        ),
        (
            "Billing/Cancellation Request",
            create_test_email(
                "I want to cancel my subscription",
                "I need to cancel my subscription. How do I do that?",
            ),
            "sent",
        ),
        (
            "Angry Complaint (Should Escalate)",
            create_test_email(
                "I'm very angry about your service",
                "I'm angry and want to file a complaint about your terrible service!",
            ),
            "escalated",
        ),
        (
            "General Question",
            create_test_email(
                "Question about features",
                "What features do you offer? I'm interested in learning more.",
            ),
            "sent",
        ),
    ]

    results = []
    for name, email, expected in test_cases:
        passed = run_test_scenario(name, email, expected)
        results.append((name, passed))

    # Summary
    print(f"\n{'='*60}")
    print("📋 TEST SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for _, p in results if p)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for name, p in results:
        status = "✅" if p else "❌"
        print(f"  {status} {name}")

    return passed == total


if __name__ == "__main__":
    import sys
    from unittest.mock import MagicMock

    success = main()
    sys.exit(0 if success else 1)
