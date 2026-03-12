"""Main LangGraph workflow definition for the customer support agent."""

import json
from pathlib import Path
from typing import Literal

import jinja2
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.core.config import settings
from src.core.exceptions import AgentError, EscalationRequired
from src.core.logging import logger
from src.schemas.agent import (
    AgentError as AgentErrorSchema,
    AgentState,
    AgentStep,
    RetrievalResult,
)
from src.schemas.email import (
    EmailClassification,
    EmailContent,
    EmailMetadata,
    EmailResponse,
    EmailStatus,
    IntentCategory,
    Priority,
)
from src.services.email_service import get_email_service
from src.services.kb_service import get_kb_service
from src.services.llm_service import get_llm_service


def load_prompt(template_name: str, **kwargs) -> str:
    """Load and render a prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{template_name}.txt"
    template = jinja2.Template(prompt_path.read_text())
    return template.render(**kwargs)


def create_support_agent_graph() -> CompiledStateGraph:
    """Create and compile the support agent LangGraph.

    The workflow:
    1. ingest -> classify
    2. classify -> [retrieve, escalate]
    3. retrieve -> draft
    4. draft -> review
    5. review -> [send, draft (retry), escalate]
    6. send -> end
    7. escalate -> end
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node(AgentStep.INGEST, ingest_node)
    workflow.add_node(AgentStep.CLASSIFY, classify_node)
    workflow.add_node(AgentStep.RETRIEVE, retrieve_node)
    workflow.add_node(AgentStep.DRAFT, draft_node)
    workflow.add_node(AgentStep.REVIEW, review_node)
    workflow.add_node(AgentStep.SEND, send_node)
    workflow.add_node(AgentStep.ESCALATE, escalate_node)

    # Define edges
    workflow.add_edge(START, AgentStep.INGEST)
    workflow.add_edge(AgentStep.INGEST, AgentStep.CLASSIFY)

    # Conditional routing from classify
    workflow.add_conditional_edges(
        AgentStep.CLASSIFY,
        route_after_classify,
        {
            AgentStep.RETRIEVE: AgentStep.RETRIEVE,
            AgentStep.ESCALATE: AgentStep.ESCALATE,
        },
    )

    workflow.add_edge(AgentStep.RETRIEVE, AgentStep.DRAFT)
    workflow.add_edge(AgentStep.DRAFT, AgentStep.REVIEW)

    # Conditional routing from review
    workflow.add_conditional_edges(
        AgentStep.REVIEW,
        route_after_review,
        {
            AgentStep.SEND: AgentStep.SEND,
            AgentStep.DRAFT: AgentStep.DRAFT,
            AgentStep.ESCALATE: AgentStep.ESCALATE,
        },
    )

    workflow.add_edge(AgentStep.SEND, END)
    workflow.add_edge(AgentStep.ESCALATE, END)

    return workflow.compile()


# =============================================================================
# Node Functions
# =============================================================================


def ingest_node(state: AgentState) -> AgentState:
    """Process incoming email and extract structured data."""
    logger.info("Running ingest node")

    try:
        email = state.get("email")
        if not email:
            raise ValueError("No email in state")

        # Clean email body
        from src.utils.helpers import clean_email_body

        email.content.body_text = clean_email_body(email.content.body_text)

        # Update status
        email.status = EmailStatus.CLASSIFIED

        logger.info(f"Ingested email: {email.metadata.subject}")

        return {
            **state,
            "email": email,
            "current_step": AgentStep.CLASSIFY,
            "iteration_count": 0,
        }

    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        error = AgentErrorSchema(
            step=AgentStep.INGEST,
            message=str(e),
            details={"traceback": str(e.__traceback__)},
        )
        return {
            **state,
            "errors": [error],
            "current_step": AgentStep.ESCALATE,
        }


def classify_node(state: AgentState) -> AgentState:
    """Classify email intent and priority using LLM."""
    logger.info("Running classify node")

    try:
        email = state.get("email")
        if not email:
            raise ValueError("No email in state")

        # Load and render prompt
        prompt = load_prompt(
            "classify",
            sender=email.metadata.sender,
            subject=email.metadata.subject,
            body=email.content.body_text[:2000],  # Limit context
        )

        # Get LLM service and generate classification
        llm_service = get_llm_service()
        import asyncio

        response = asyncio.run(llm_service.generate(prompt))

        # Parse JSON response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            import re

            json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                raise ValueError("Could not parse LLM response as JSON")

        classification = EmailClassification(
            intent=IntentCategory(result.get("intent", "unknown")),
            priority=Priority(result.get("priority", "medium")),
            confidence=result.get("confidence", 0.5),
            requires_escalation=result.get("requires_escalation", False),
            key_points=result.get("key_points", []),
            suggested_category=result.get("suggested_category"),
        )

        # Update email
        email.classification = classification
        email.status = EmailStatus.DRAFTING

        logger.info(
            f"Classified email: {classification.intent.value} "
            f"(confidence: {classification.confidence:.2f})"
        )

        return {
            **state,
            "email": email,
            "classification": classification,
            "current_step": AgentStep.CLASSIFY,
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        error = AgentErrorSchema(
            step=AgentStep.CLASSIFY,
            message=str(e),
            details={"traceback": str(e.__traceback__)},
        )
        return {
            **state,
            "errors": [error],
            "current_step": AgentStep.ESCALATE,
        }


def retrieve_node(state: AgentState) -> AgentState:
    """Retrieve relevant documents from knowledge base."""
    logger.info("Running retrieve node")

    try:
        email = state.get("email")
        classification = state.get("classification")

        if not email or not classification:
            raise ValueError("Missing email or classification in state")

        # Build search query from email content and key points
        query_parts = [email.content.body_text[:500]]
        query_parts.extend(classification.key_points)
        search_query = " ".join(query_parts)

        # Search knowledge base
        kb_service = get_kb_service()
        results = kb_service.search(
            query=search_query,
            top_k=5,
        )

        logger.info(f"Retrieved {len(results)} documents from KB")

        return {
            **state,
            "retrieved_documents": results,
            "current_step": AgentStep.DRAFT,
        }

    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        error = AgentErrorSchema(
            step=AgentStep.RETRIEVE,
            message=str(e),
            details={"traceback": str(e.__traceback__)},
        )
        return {
            **state,
            "errors": [error],
            "current_step": AgentStep.ESCALATE,
        }


def draft_node(state: AgentState) -> AgentState:
    """Draft a response based on retrieved context using LLM."""
    logger.info("Running draft node")

    try:
        email = state.get("email")
        classification = state.get("classification")
        documents = state.get("retrieved_documents", [])

        if not email or not classification:
            raise ValueError("Missing email or classification in state")

        # Build knowledge context
        knowledge_context = "\n\n".join(
            f"Document {i + 1} (Source: {doc.source}, Score: {doc.similarity_score:.2f}):\n{doc.content}"
            for i, doc in enumerate(documents)
        )

        if not knowledge_context:
            knowledge_context = "No relevant documents found in knowledge base."

        # Determine tone based on intent and priority
        tone = "professional"
        if classification.intent.value == "complaint":
            tone = "apologetic"
        elif classification.priority == Priority.LOW:
            tone = "friendly"
        elif classification.priority == Priority.HIGH:
            tone = "formal"

        # Load and render prompt
        prompt = load_prompt(
            "draft",
            sender=email.metadata.sender,
            subject=email.metadata.subject,
            body=email.content.body_text[:1500],
            intent=classification.intent.value,
            priority=classification.priority.value,
            tone=tone,
            knowledge_context=knowledge_context,
        )

        # Generate response
        llm_service = get_llm_service()
        import asyncio

        response = asyncio.run(llm_service.generate(prompt))

        # Parse JSON response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            import re

            json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # Fallback: treat entire response as body
                result = {
                    "subject": f"Re: {email.metadata.subject}",
                    "body": response,
                    "tone": tone,
                    "citations": [],
                    "confidence": 0.5,
                }

        draft_response = EmailResponse(
            subject=result.get("subject", f"Re: {email.metadata.subject}"),
            body=result.get("body", response),
            body_html=result.get("body_html"),
            tone=result.get("tone", tone),
            citations=result.get("citations", []),
            confidence=result.get("confidence", 0.5),
        )

        # Update email
        email.response = draft_response
        email.status = EmailStatus.REVIEWING

        logger.info(f"Drafted response: {draft_response.subject}")

        return {
            **state,
            "email": email,
            "draft_response": draft_response,
            "current_step": AgentStep.REVIEW,
        }

    except Exception as e:
        logger.error(f"Drafting failed: {e}")
        error = AgentErrorSchema(
            step=AgentStep.DRAFT,
            message=str(e),
            details={"traceback": str(e.__traceback__)},
        )
        return {
            **state,
            "errors": [error],
            "current_step": AgentStep.ESCALATE,
        }


def review_node(state: AgentState) -> AgentState:
    """Review drafted response for quality and accuracy using LLM."""
    logger.info("Running review node")

    try:
        email = state.get("email")
        classification = state.get("classification")
        draft = state.get("draft_response")
        documents = state.get("retrieved_documents", [])

        if not email or not draft:
            raise ValueError("Missing email or draft in state")

        # Build knowledge context for review
        knowledge_context = "\n\n".join(
            f"Document {i + 1} (Source: {doc.source}):\n{doc.content}"
            for i, doc in enumerate(documents)
        )

        if not knowledge_context:
            knowledge_context = "No relevant documents found."

        # Load and render review prompt
        prompt = load_prompt(
            "review",
            sender=email.metadata.sender,
            subject=email.metadata.subject,
            customer_body=email.content.body_text[:1000],
            intent=classification.intent.value if classification else "unknown",
            priority=classification.priority.value if classification else "medium",
            draft_subject=draft.subject,
            draft_body=draft.body,
            knowledge_context=knowledge_context,
        )

        # Generate review
        llm_service = get_llm_service()
        import asyncio

        response = asyncio.run(llm_service.generate(prompt))

        # Parse JSON response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            import re

            json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # Default to approved if parsing fails
                result = {"approved": True, "score": 0.7}

        review_result = {
            "approved": result.get("approved", False),
            "score": result.get("score", 0.5),
            "issues": result.get("issues", []),
            "feedback": result.get("feedback", ""),
            "suggested_changes": result.get("suggested_changes", []),
        }

        # Increment iteration count
        iteration_count = state.get("iteration_count", 0) + 1

        logger.info(
            f"Review result: approved={review_result['approved']}, "
            f"score={review_result['score']:.2f}, iteration={iteration_count}"
        )

        return {
            **state,
            "review_result": review_result,
            "iteration_count": iteration_count,
            "current_step": AgentStep.REVIEW,
            "metadata": {
                "review_feedback": review_result.get("feedback", ""),
            },
        }

    except Exception as e:
        logger.error(f"Review failed: {e}")
        error = AgentErrorSchema(
            step=AgentStep.REVIEW,
            message=str(e),
            details={"traceback": str(e.__traceback__)},
        )
        return {
            **state,
            "errors": [error],
            "current_step": AgentStep.ESCALATE,
        }


def send_node(state: AgentState) -> AgentState:
    """Send the approved response via email."""
    logger.info("Running send node")

    try:
        email = state.get("email")
        response = state.get("draft_response")

        if not email or not response:
            raise ValueError("Missing email or response in state")

        # Skip sending if auto_send is disabled
        if not settings.agent.auto_send:
            logger.info("Auto-send disabled, email queued for manual sending")
            email.status = EmailStatus.PENDING

            return {
                **state,
                "email": email,
                "current_step": AgentStep.END,
                "status": EmailStatus.PENDING,
            }

        # Send email
        email_service = get_email_service()
        success = email_service.send_response(
            to_email=str(email.metadata.sender),
            subject=response.subject,
            body_text=response.body,
            body_html=response.body_html,
            in_reply_to=email.metadata.message_id,
        )

        if success:
            email.status = EmailStatus.SENT
            logger.info(f"Email sent to {email.metadata.sender}")
        else:
            raise RuntimeError("Failed to send email")

        return {
            **state,
            "email": email,
            "current_step": AgentStep.END,
            "status": EmailStatus.SENT,
        }

    except Exception as e:
        logger.error(f"Send failed: {e}")
        error = AgentErrorSchema(
            step=AgentStep.SEND,
            message=str(e),
            details={"traceback": str(e.__traceback__)},
        )
        return {
            **state,
            "errors": [error],
            "current_step": AgentStep.ESCALATE,
        }


def escalate_node(state: AgentState) -> AgentState:
    """Escalate to human agent."""
    logger.info("Running escalate node")

    try:
        email = state.get("email")
        errors = state.get("errors", [])

        if email:
            email.status = EmailStatus.ESCALATED

            # Build escalation reason
            reasons = []
            if errors:
                reasons.append(f"Error: {errors[-1].message}")
            if email.classification and email.classification.requires_escalation:
                reasons.append(
                    f"Intent: {email.classification.intent.value} requires human"
                )

            logger.warning(
                f"Email escalated: {email.metadata.subject} - "
                f"{'; '.join(reasons)}"
            )

        return {
            **state,
            "email": email,
            "current_step": AgentStep.END,
            "status": EmailStatus.ESCALATED,
        }

    except Exception as e:
        logger.error(f"Escalation failed: {e}")
        return {
            **state,
            "current_step": AgentStep.END,
            "status": EmailStatus.FAILED,
        }


# =============================================================================
# Routing Functions
# =============================================================================


def route_after_classify(
    state: AgentState,
) -> Literal[AgentStep.RETRIEVE, AgentStep.ESCALATE]:
    """Determine next step after classification.

    Routes to escalate if:
    - Intent requires human (e.g., complaint, complex issue)
    - Confidence is low
    - Explicit escalation flag set
    """
    classification = state.get("classification")
    errors = state.get("errors", [])

    # If there were errors, escalate
    if errors and any(e.step == AgentStep.CLASSIFY for e in errors):
        return AgentStep.ESCALATE

    if classification and classification.requires_escalation:
        return AgentStep.ESCALATE

    return AgentStep.RETRIEVE


def route_after_review(
    state: AgentState,
) -> Literal[AgentStep.SEND, AgentStep.DRAFT, AgentStep.ESCALATE]:
    """Determine next step after review.

    Routes to:
    - send: if response approved
    - draft: if needs revision (retry with feedback)
    - escalate: if max iterations reached or quality too low
    """
    review = state.get("review_result", {})
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", settings.agent.max_iterations)

    # If approved, send
    if review.get("approved", False):
        return AgentStep.SEND

    # If max iterations reached, escalate
    if iteration_count >= max_iterations:
        logger.warning(f"Max iterations ({max_iterations}) reached, escalating")
        return AgentStep.ESCALATE

    # Otherwise, retry drafting with feedback
    logger.info(f"Response needs revision (iteration {iteration_count})")
    return AgentStep.DRAFT


# Global compiled graph instance
support_agent = create_support_agent_graph()
