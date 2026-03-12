"""Email API routes."""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from src.agent.graph import support_agent
from src.core.config import settings
from src.core.logging import logger
from src.schemas.agent import AgentState
from src.schemas.email import (
    CustomerEmail,
    EmailContent,
    EmailCreateRequest,
    EmailMetadata,
    EmailProcessResponse,
    EmailStatus,
)
from src.services.email_service import get_email_service
from src.utils.helpers import generate_id

router = APIRouter()


def process_email_through_agent(email: CustomerEmail) -> CustomerEmail:
    """Process an email through the agent workflow."""
    try:
        # Initialize state
        initial_state: AgentState = {
            "email": email,
            "current_step": None,
            "next_step": None,
            "classification": None,
            "retrieved_documents": [],
            "draft_response": None,
            "review_result": None,
            "iteration_count": 0,
            "max_iterations": settings.agent.max_iterations,
            "status": EmailStatus.PENDING,
            "errors": [],
            "metadata": {},
        }

        # Invoke the graph
        final_state = support_agent.invoke(initial_state)

        # Return the processed email
        return final_state.get("email", email)

    except Exception as e:
        logger.error(f"Agent processing failed: {e}")
        email.status = EmailStatus.FAILED
        raise


@router.post(
    "/process",
    response_model=EmailProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process a new email",
    description="Submit a new customer email for agent processing",
)
async def process_email(request: EmailCreateRequest) -> EmailProcessResponse:
    """Process a new customer email through the agent workflow."""
    try:
        # Create email object
        metadata = EmailMetadata(
            message_id=generate_id(),
            subject=request.subject,
            sender=request.sender,
            sender_name=request.sender_name,
            to=["support@company.com"],  # Configurable
            received_at=datetime.utcnow(),
        )

        content = EmailContent(
            body_text=request.body,
        )

        email = CustomerEmail(
            id=generate_id(),
            metadata=metadata,
            content=content,
        )

        logger.info(f"Processing email: {email.id} - {email.metadata.subject}")

        # Process through agent
        processed_email = process_email_through_agent(email)

        return EmailProcessResponse(
            email_id=processed_email.id,
            status=processed_email.status,
            classification=processed_email.classification,
            response=processed_email.response,
            message=f"Email processed with status: {processed_email.status.value}",
        )

    except Exception as e:
        logger.error(f"Failed to process email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post(
    "/fetch",
    response_model=list[EmailProcessResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch and process unread emails",
    description="Fetch unread emails from IMAP and process them",
)
async def fetch_and_process_emails() -> list[EmailProcessResponse]:
    """Fetch unread emails from IMAP and process through the agent."""
    try:
        email_service = get_email_service()
        results = []

        logger.info("Fetching unread emails from IMAP")

        for email in email_service.fetch_unread():
            try:
                logger.info(f"Processing fetched email: {email.metadata.subject}")
                processed_email = process_email_through_agent(email)

                results.append(
                    EmailProcessResponse(
                        email_id=processed_email.id,
                        status=processed_email.status,
                        classification=processed_email.classification,
                        response=processed_email.response,
                        message=f"Processed: {processed_email.status.value}",
                    )
                )

            except Exception as e:
                logger.error(f"Failed to process email {email.id}: {e}")
                results.append(
                    EmailProcessResponse(
                        email_id=email.id,
                        status=EmailStatus.FAILED,
                        message=f"Failed: {str(e)}",
                    )
                )

        return results

    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get(
    "/{email_id}",
    response_model=CustomerEmail,
    status_code=status.HTTP_200_OK,
    summary="Get email by ID",
)
async def get_email(email_id: str) -> CustomerEmail:
    """Retrieve a processed email by ID."""
    # TODO: Implement persistence layer
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Email persistence not implemented yet",
    )


@router.get(
    "/",
    response_model=list[CustomerEmail],
    status_code=status.HTTP_200_OK,
    summary="List emails",
)
async def list_emails(
    status: EmailStatus | None = None,
    limit: int = 10,
    offset: int = 0,
) -> list[CustomerEmail]:
    """List processed emails with optional filtering."""
    # TODO: Implement persistence layer
    return []


@router.post(
    "/{email_id}/escalate",
    status_code=status.HTTP_200_OK,
    summary="Escalate email to human",
)
async def escalate_email(email_id: str) -> dict:
    """Manually escalate an email to human agents."""
    # TODO: Implement persistence layer interaction
    logger.info(f"Manually escalating email: {email_id}")
    return {"email_id": email_id, "status": "escalated"}


@router.post(
    "/{email_id}/send",
    status_code=status.HTTP_200_OK,
    summary="Send pending email response",
)
async def send_pending_response(email_id: str) -> dict:
    """Send a pending email response (manual approval workflow)."""
    # TODO: Implement persistence layer
    logger.info(f"Sending pending response for email: {email_id}")
    return {"email_id": email_id, "status": "sent"}
