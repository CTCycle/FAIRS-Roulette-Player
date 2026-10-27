# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from server.common import path as shared_paths


# Successful requests to these routes are polled or probed continuously and carry
# no diagnostic value; failures (status >= 400) are always logged.
QUIET_ACCESS_PATHS = frozenset(
    {
        "/api/health",
        "/api/training/status",
    }
)
QUIET_ACCESS_PREFIXES = ("/api/training/jobs/", "/assets/")
NOISY_LIBRARY_LOGGERS = ("matplotlib", "asyncio", "PIL", "python_multipart", "h5py")


###############################################################################
class QuietAccessFilter(logging.Filter):
    """Drop successful polling, preflight, and static-asset access records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            _client, method, target, _version, status = record.args  # type: ignore[misc]
            path = str(target).split("?", 1)[0]
            if int(status) >= 400:
                return True
        except (TypeError, ValueError):
            return True
        if method == "OPTIONS":
            return False
        if method != "GET":
            return True
        return path not in QUIET_ACCESS_PATHS and not path.startswith(
            QUIET_ACCESS_PREFIXES
        )


###############################################################################
def _build_log_config(log_directory: Path) -> dict[str, Any]:
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root_level = os.environ.get("FAIRS_LOG_LEVEL", "INFO").upper()
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
        "filters": {"quiet_access": {"()": QuietAccessFilter}},
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
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "filters": ["quiet_access"],
                "propagate": False,
            },
            **{
                name: {"level": "WARNING"} for name in NOISY_LIBRARY_LOGGERS
            },
        },
        "root": {
            "level": root_level,
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
