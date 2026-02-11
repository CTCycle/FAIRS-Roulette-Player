"""
Pytest configuration for FAIRS E2E tests.
Provides fixtures for Playwright page objects and API client.
"""

import os

import pytest


def _build_base_url(
    host_env: str, port_env: str, default_host: str, default_port: str
) -> str:
    host = os.getenv(host_env, default_host)
    port = os.getenv(port_env, default_port)
    return f"http://{host}:{port}"


# Base URLs - prefer explicit env vars, then fall back to host/port pairs.
UI_BASE_URL = (
    os.getenv("UI_BASE_URL")
    or os.getenv("UI_URL")
    or _build_base_url("UI_HOST", "UI_PORT", "127.0.0.1", "7861")
)
API_BASE_URL = os.getenv("API_BASE_URL") or _build_base_url(
    "FASTAPI_HOST", "FASTAPI_PORT", "127.0.0.1", "8000"
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
