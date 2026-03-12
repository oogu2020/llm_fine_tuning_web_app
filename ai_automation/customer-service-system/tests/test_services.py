"""Tests for service layer."""

import pytest
from unittest.mock import MagicMock, patch, mock_open

from src.core.exceptions import EmailClientError, LLMError, VectorStoreError
from src.services.email_service import EmailService
from src.services.kb_service import KnowledgeBaseService
from src.services.llm_service import LLMService


class TestLLMService:
    """Tests for LLM service."""

    @patch("src.services.llm_service.settings")
    def test_llm_service_anthropic(self, mock_settings):
        """Test Anthropic client creation."""
        mock_settings.llm.provider = "anthropic"
        mock_settings.llm.model = "claude-3-5-sonnet"
        mock_settings.llm.temperature = 0.3
        mock_settings.llm.max_tokens = 4096
        mock_settings.anthropic_api_key = "test-key"

        with patch("src.services.llm_service.ChatAnthropic") as mock_chat:
            mock_chat.return_value = MagicMock()

            service = LLMService()
            client = service.get_client()

            mock_chat.assert_called_once()

    @patch("src.services.llm_service.settings")
    def test_llm_service_missing_api_key(self, mock_settings):
        """Test error when API key is missing."""
        mock_settings.llm.provider = "anthropic"
        mock_settings.anthropic_api_key = ""

        service = LLMService()

        with pytest.raises(Exception):
            service.get_client()


class TestEmailService:
    """Tests for email service."""

    @patch("src.services.email_service.settings")
    def test_email_service_connect_imap(self, mock_settings):
        """Test IMAP connection."""
        mock_settings.email.host = "imap.gmail.com"
        mock_settings.email.port = 993
        mock_settings.email.user = "test@test.com"
        mock_settings.email.password = "password"

        with patch("imaplib.IMAP4_SSL") as mock_imap:
            mock_client = MagicMock()
            mock_imap.return_value = mock_client

            service = EmailService()
            service.connect_imap()

            mock_imap.assert_called_with("imap.gmail.com", 993)
            mock_client.login.assert_called_with("test@test.com", "password")

    @patch("src.services.email_service.settings")
    def test_email_service_send_response(self, mock_settings):
        """Test sending email response."""
        mock_settings.smtp.host = "smtp.gmail.com"
        mock_settings.smtp.port = 587
        mock_settings.smtp.use_tls = True
        mock_settings.smtp.user = "test@test.com"
        mock_settings.smtp.password = "password"

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            service = EmailService()
            result = service.send_response(
                to_email="customer@example.com",
                subject="Re: Test",
                body_text="Test response",
            )

            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()


class TestKBService:
    """Tests for knowledge base service."""

    @patch("src.services.kb_service.settings")
    def test_kb_service_search(self, mock_settings):
        """Test knowledge base search."""
        mock_settings.chroma.persist_dir = "./data/chroma"
        mock_settings.chroma.collection_name = "test_kb"
        mock_settings.kb.embedding_model = "all-MiniLM-L6-v2"

        with patch("chromadb.PersistentClient") as mock_client:
            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                "documents": [["Test document"]],
                "metadatas": [[{"source": "test.md"}]],
                "distances": [[0.1]],
            }

            mock_chroma = MagicMock()
            mock_chroma.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_chroma

            service = KnowledgeBaseService()
            results = service.search("test query", top_k=5)

            assert len(results) == 1
            assert results[0].content == "Test document"
            assert results[0].source == "test.md"

    @patch("src.services.kb_service.settings")
    def test_kb_service_add_document(self, mock_settings):
        """Test adding document to KB."""
        mock_settings.chroma.persist_dir = "./data/chroma"
        mock_settings.chroma.collection_name = "test_kb"
        mock_settings.kb.embedding_model = "all-MiniLM-L6-v2"

        with patch("chromadb.PersistentClient") as mock_client:
            mock_collection = MagicMock()
            mock_chroma = MagicMock()
            mock_chroma.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_chroma

            service = KnowledgeBaseService()
            result = service.add_document(
                content="Test content",
                source="test.md",
            )

            assert result is True
            mock_collection.add.assert_called_once()
