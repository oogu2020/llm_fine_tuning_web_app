"""Email service for IMAP/SMTP operations."""

import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Generator

from src.core.config import settings
from src.core.exceptions import EmailClientError
from src.core.logging import logger
from src.schemas.email import CustomerEmail, EmailContent, EmailMetadata


class EmailService:
    """Service for email operations."""

    def __init__(self):
        self._imap_client: imaplib.IMAP4_SSL | None = None
        self._settings = settings.email
        self._smtp_settings = settings.smtp

    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server."""
        try:
            client = imaplib.IMAP4_SSL(self._settings.host, self._settings.port)
            client.login(self._settings.user, self._settings.password)
            logger.info(f"Connected to IMAP: {self._settings.host}")
            return client
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            raise EmailClientError(f"Failed to connect to IMAP: {e}") from e

    def fetch_unread(self) -> Generator[CustomerEmail, None, None]:
        """Fetch unread emails from inbox."""
        try:
            client = self.connect_imap()
            client.select(self._settings.folder)

            # Search for unread messages
            _, message_ids = client.search(None, "(UNSEEN)")
            message_ids = message_ids[0].split()

            logger.info(f"Found {len(message_ids)} unread emails")

            for msg_id in message_ids:
                try:
                    _, msg_data = client.fetch(msg_id, "(RFC822)")
                    raw_email = msg_data[0][1]

                    # Parse email
                    import email

                    msg = email.message_from_bytes(raw_email)

                    # Extract content
                    body_text = ""
                    body_html = None

                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body_text = part.get_payload(decode=True).decode(
                                    "utf-8", errors="ignore"
                                )
                            elif content_type == "text/html":
                                body_html = part.get_payload(decode=True).decode(
                                    "utf-8", errors="ignore"
                                )
                    else:
                        body_text = msg.get_payload(decode=True).decode(
                            "utf-8", errors="ignore"
                        )

                    # Parse sender
                    from_header = msg.get("From", "")
                    sender_email = from_header
                    sender_name = ""

                    import re

                    match = re.match(r"^(.*?)\s*<(.+?)>$", from_header)
                    if match:
                        sender_name = match.group(1).strip('"')
                        sender_email = match.group(2)

                    from datetime import datetime

                    metadata = EmailMetadata(
                        message_id=msg.get("Message-ID", ""),
                        thread_id=msg.get("In-Reply-To", None),
                        received_at=datetime.now(),  # Parse from date header ideally
                        subject=msg.get("Subject", "No Subject"),
                        sender=sender_email,
                        sender_name=sender_name,
                        to=[addr.strip() for addr in msg.get("To", "").split(",")],
                        cc=[
                            addr.strip()
                            for addr in msg.get("Cc", "").split(",")
                            if addr.strip()
                        ],
                    )

                    content = EmailContent(
                        body_text=body_text,
                        body_html=body_html,
                    )

                    from src.utils.helpers import generate_id

                    email_obj = CustomerEmail(
                        id=generate_id(),
                        metadata=metadata,
                        content=content,
                    )

                    yield email_obj

                except Exception as e:
                    logger.error(f"Failed to parse email {msg_id}: {e}")
                    continue

            client.close()
            client.logout()

        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            raise EmailClientError(f"Fetch failed: {e}") from e

    def send_response(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        in_reply_to: str | None = None,
    ) -> bool:
        """Send email response via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._smtp_settings.user
            msg["To"] = to_email

            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to

            msg.attach(MIMEText(body_text, "plain"))

            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(self._smtp_settings.host, self._smtp_settings.port) as server:
                if self._smtp_settings.use_tls:
                    server.starttls()
                server.login(self._smtp_settings.user, self._smtp_settings.password)
                server.send_message(msg)

            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise EmailClientError(f"Send failed: {e}") from e

    def mark_processed(self, message_id: str) -> bool:
        """Move email to processed folder."""
        # TODO: Implement move logic
        pass


def get_email_service() -> EmailService:
    """Get email service instance."""
    return EmailService()
