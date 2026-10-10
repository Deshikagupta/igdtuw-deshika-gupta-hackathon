"""Application logging configuration."""

import logging


def configure_logging(log_level: str = "INFO") -> None:
    """Configure application-wide logging."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )
