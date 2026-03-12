"""Application logging configuration."""

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from src.core.config import settings


def setup_logging() -> logging.Logger:
    """Configure application logging with Rich and file handlers."""

    # Create logs directory if needed
    log_dir = Path("./data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Root logger
    logger = logging.getLogger("customer_support_agent")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Rich console handler
    console = Console(stderr=True)
    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        tracebacks_show_locals=settings.debug,
        markup=True,
    )
    rich_handler.setLevel(logging.INFO)

    # File handler for persistent logs
    file_handler = logging.FileHandler(
        log_dir / "agent.log",
        mode="a",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers
    logger.addHandler(rich_handler)
    logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logging()
