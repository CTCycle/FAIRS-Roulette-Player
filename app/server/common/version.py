from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

PACKAGE_NAME = "fairs-server"

###############################################################################
def get_application_version() -> str:
    """Return the installed application version from package metadata."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError as exc:
        raise RuntimeError(
            f"Installed package metadata is missing for {PACKAGE_NAME}."
        ) from exc


__all__ = ["get_application_version"]
