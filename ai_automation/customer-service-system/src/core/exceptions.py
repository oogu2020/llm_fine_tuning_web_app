"""Custom exceptions for the customer support agent."""


class AgentException(Exception):
    """Base exception for all agent errors."""

    pass


class ConfigurationError(AgentException):
    """Raised when there's a configuration issue."""

    pass


class EmailClientError(AgentException):
    """Raised when email operations fail."""

    pass


class LLMError(AgentException):
    """Raised when LLM API calls fail."""

    pass


class VectorStoreError(AgentException):
    """Raised when vector store operations fail."""

    pass


class KnowledgeBaseError(AgentException):
    """Raised when knowledge base operations fail."""

    pass


class EscalationRequired(AgentException):
    """Raised when human escalation is required."""

    def __init__(self, message: str, reason: str = ""):
        super().__init__(message)
        self.reason = reason
