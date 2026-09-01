from __future__ import annotations

import logging
import logging.config
from datetime import datetime
from pathlib import Path
from typing import Any

from server.common import path as shared_paths


###############################################################################
def _build_log_config(log_directory: Path) -> dict[str, Any]:
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = log_directory / f"FAIRS_{current_timestamp}.log"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%d-%m-%Y %H:%M:%S",
            },
            "minimal": {
                "format": "[%(levelname)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "minimal",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "default",
                "filename": str(log_filename),
                "mode": "a",
                "delay": True,
            },
        },
        "loggers": {
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "matplotlib": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
        },
    }


logger = logging.getLogger()
_configured = False


###############################################################################
def configure_logging(*, force: bool = False) -> None:
    """Configure application logging at an explicit runtime boundary."""
    global _configured
    if _configured and not force:
        return

    resolved_directory = Path(shared_paths.LOGS_PATH)
    resolved_directory.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(_build_log_config(resolved_directory))
    _configured = True


###############################################################################
def close_application_logging() -> None:
    """Close only file handlers owned by the FAIRS application."""
    global _configured
    resolved_directory = Path(shared_paths.LOGS_PATH).resolve()
    logger_objects = [logging.getLogger()]
    logger_objects.extend(
        value
        for value in logging.Logger.manager.loggerDict.values()
        if isinstance(value, logging.Logger)
    )
    seen_handlers: set[int] = set()
    for logger_object in logger_objects:
        for handler in list(logger_object.handlers):
            if not isinstance(handler, logging.FileHandler):
                continue
            filename = Path(handler.baseFilename).resolve()
            if resolved_directory not in filename.parents:
                continue
            logger_object.removeHandler(handler)
            if id(handler) not in seen_handlers:
                handler.close()
                seen_handlers.add(id(handler))
    _configured = False
