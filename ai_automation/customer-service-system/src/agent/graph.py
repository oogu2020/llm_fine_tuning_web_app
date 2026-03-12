"""Main LangGraph workflow definition for the customer support agent."""

from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.core.logging import logger
from src.schemas.agent import AgentState, AgentStep


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
# Node Functions (Placeholders - to be implemented)
# =============================================================================


def ingest_node(state: AgentState) -> AgentState:
    """Process incoming email and extract structured data."""
    logger.info("Running ingest node")
    # TODO: Implement email ingestion logic
    return {**state, "current_step": AgentStep.CLASSIFY}


def classify_node(state: AgentState) -> AgentState:
    """Classify email intent and priority."""
    logger.info("Running classify node")
    # TODO: Implement classification logic
    return {**state, "current_step": AgentStep.CLASSIFY}


def retrieve_node(state: AgentState) -> AgentState:
    """Retrieve relevant documents from knowledge base."""
    logger.info("Running retrieve node")
    # TODO: Implement retrieval logic
    return {**state, "current_step": AgentStep.DRAFT}


def draft_node(state: AgentState) -> AgentState:
    """Draft a response based on retrieved context."""
    logger.info("Running draft node")
    # TODO: Implement drafting logic
    return {**state, "current_step": AgentStep.REVIEW}


def review_node(state: AgentState) -> AgentState:
    """Review drafted response for quality and accuracy."""
    logger.info("Running review node")
    # TODO: Implement review logic
    return {**state, "current_step": AgentStep.REVIEW}


def send_node(state: AgentState) -> AgentState:
    """Send the approved response via email."""
    logger.info("Running send node")
    # TODO: Implement send logic
    return {**state, "current_step": AgentStep.END}


def escalate_node(state: AgentState) -> AgentState:
    """Escalate to human agent."""
    logger.info("Running escalate node")
    # TODO: Implement escalation logic
    return {**state, "current_step": AgentStep.END}


# =============================================================================
# Routing Functions
# =============================================================================


def route_after_classify(state: AgentState) -> Literal[AgentStep.RETRIEVE, AgentStep.ESCALATE]:
    """Determine next step after classification.

    Routes to escalate if:
    - Intent requires human (e.g., complaint, complex issue)
    - Confidence is low
    - Explicit escalation flag set
    """
    classification = state.get("classification")

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
    max_iterations = state.get("max_iterations", 5)

    if review.get("approved", False):
        return AgentStep.SEND

    if iteration_count >= max_iterations:
        return AgentStep.ESCALATE

    return AgentStep.DRAFT


# Global compiled graph instance
support_agent = create_support_agent_graph()
