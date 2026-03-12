"""LLM client service for interacting with Anthropic/OpenAI."""

from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.core.exceptions import ConfigurationError, LLMError
from src.core.logging import logger


class LLMService:
    """Service for LLM operations."""

    def __init__(self):
        self._client: BaseChatModel | None = None
        self._settings = settings.llm

    def get_client(self) -> BaseChatModel:
        """Get or create LLM client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> BaseChatModel:
        """Initialize the appropriate LLM client."""
        try:
            if self._settings.provider == "anthropic":
                if not settings.anthropic_api_key:
                    raise ConfigurationError("ANTHROPIC_API_KEY not set")

                return ChatAnthropic(
                    model=self._settings.model,
                    temperature=self._settings.temperature,
                    max_tokens=self._settings.max_tokens,
                    api_key=settings.anthropic_api_key,
                )

            elif self._settings.provider == "openai":
                if not settings.openai_api_key:
                    raise ConfigurationError("OPENAI_API_KEY not set")

                return ChatOpenAI(
                    model=self._settings.model,
                    temperature=self._settings.temperature,
                    max_tokens=self._settings.max_tokens,
                    api_key=settings.openai_api_key,
                )

            else:
                raise ConfigurationError(f"Unknown LLM provider: {self._settings.provider}")

        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise LLMError(f"LLM initialization failed: {e}") from e

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from LLM."""
        try:
            client = self.get_client()
            messages = [{"role": "user", "content": prompt}]
            response = await client.ainvoke(messages, **kwargs)
            return str(response.content)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise LLMError(f"Generation failed: {e}") from e


@lru_cache
def get_llm_service() -> LLMService:
    """Get cached LLM service instance."""
    return LLMService()
