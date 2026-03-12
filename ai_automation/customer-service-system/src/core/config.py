"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: Literal["anthropic", "openai"] = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)


class EmailSettings(BaseSettings):
    """Email server configuration."""

    model_config = SettingsConfigDict(env_prefix="EMAIL_")

    host: str = "imap.gmail.com"
    port: int = 993
    user: str = ""
    password: str = ""
    use_ssl: bool = True
    poll_interval_seconds: int = 60
    folder: str = "INBOX"
    processed_folder: str = "Processed"


class SMTPSettings(BaseSettings):
    """SMTP server configuration."""

    model_config = SettingsConfigDict(env_prefix="SMTP_")

    host: str = "smtp.gmail.com"
    port: int = 587
    use_tls: bool = True
    user: str = ""
    password: str = ""


class ChromaSettings(BaseSettings):
    """ChromaDB vector store configuration."""

    model_config = SettingsConfigDict(env_prefix="CHROMA_")

    persist_dir: str = "./data/chroma"
    collection_name: str = "support_kb"


class KBSettings(BaseSettings):
    """Knowledge base configuration."""

    model_config = SettingsConfigDict(env_prefix="KB_")

    documents_dir: str = "./src/knowledge_base/documents"
    chunk_size: int = 500
    chunk_overlap: int = 50


class AgentSettings(BaseSettings):
    """Agent behavior configuration."""

    model_config = SettingsConfigDict(env_prefix="AGENT_")

    max_iterations: int = 5
    escalation_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    auto_send: bool = False


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # App Info
    app_name: str = Field(default="Customer Support Email Agent", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")

    # API Settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=1, alias="API_WORKERS")

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    kb: KBSettings = Field(default_factory=KBSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
