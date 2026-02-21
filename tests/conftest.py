"""
Pytest configuration for FAIRS E2E tests.
Provides fixtures for Playwright page objects and API client.
"""

import os

import pytest


def _normalize_connect_host(host: str) -> str:
    if host in {"0.0.0.0", "::", "[::]"}:
        return "127.0.0.1"
    return host


def _build_base_url(
    host_env: str, port_env: str, default_host: str, default_port: str
) -> str:
    host = _normalize_connect_host(os.getenv(host_env, default_host))
    port = os.getenv(port_env, default_port)
    return f"http://{host}:{port}"


# Base URLs - prefer explicit app test URLs, then legacy vars, then host/port pairs.
UI_BASE_URL = (
    os.getenv("APP_TEST_FRONTEND_URL")
    or os.getenv("UI_BASE_URL")
    or os.getenv("UI_URL")
    or _build_base_url("UI_HOST", "UI_PORT", "127.0.0.1", "7861")
)
API_BASE_URL = (
    os.getenv("APP_TEST_BACKEND_URL")
    or os.getenv("API_BASE_URL")
    or _build_base_url("FASTAPI_HOST", "FASTAPI_PORT", "127.0.0.1", "8000")
)


@pytest.fixture(scope="session")
def base_url() -> str:
    """Returns the base URL of the UI."""
    return UI_BASE_URL


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Returns the base URL of the API."""
    return API_BASE_URL


@pytest.fixture
def api_context(playwright):
    """
    Creates an API request context for making direct HTTP calls.
    Useful for testing backend endpoints independently of the UI.
    """
    context = playwright.request.new_context(base_url=API_BASE_URL)
    yield context
    context.dispose()
