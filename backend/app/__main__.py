"""`python -m app` entry point: starts Uvicorn using BACKEND_HOST / BACKEND_PORT."""

import sys

import uvicorn

from app.config import get_settings
from app.exceptions import ConfigurationError


def main() -> None:
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        sys.exit(f"\n{exc}\n")

    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()