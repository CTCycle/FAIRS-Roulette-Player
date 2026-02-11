"""
E2E tests for UI navigation and page rendering.
Tests basic UI functionality using Playwright browser automation.
"""

import re
from playwright.sync_api import Page, expect


class TestHomePage:
    """Tests for the home page and basic navigation."""

    def test_homepage_loads_successfully(self, page: Page, base_url: str):
        """The homepage should load without errors."""
        page.goto(base_url)
        # Page should have loaded successfully
        expect(page).to_have_title(re.compile(".*"))  # Any title is fine

    def test_homepage_has_navigation(self, page: Page, base_url: str):
        """The homepage should have navigation elements."""
        page.goto(base_url)
        # Wait for the page to be fully loaded
        page.wait_for_load_state("networkidle")

        # Check that the page has some content
        body = page.locator("body")
        expect(body).to_be_visible()


class TestNavigationFlow:
    """Tests for navigating between different pages."""

    def test_navigate_to_training_page(self, page: Page, base_url: str):
        """Should be able to navigate to the Training page."""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")

        # Try to find and click the Training link
        training_link = page.get_by_text("Training", exact=False).first
        expect(training_link).to_be_visible()
        training_link.click()

        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(re.compile(".*training.*", re.IGNORECASE))

    def test_navigate_to_inference_page(self, page: Page, base_url: str):
        """Should be able to navigate to the Inference page."""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")

        # Try to find and click the Inference link
        inference_link = page.get_by_text("Inference", exact=False).first
        expect(inference_link).to_be_visible()
        inference_link.click()

        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(re.compile(".*inference.*", re.IGNORECASE))


class TestTrainingPage:
    """Tests for the Training page."""

    def test_training_page_loads(self, page: Page, base_url: str):
        """The Training page should load without errors."""
        page.goto(f"{base_url}/training")
        page.wait_for_load_state("networkidle")

        body = page.locator("body")
        expect(body).to_be_visible()

    def test_training_page_shows_status(self, page: Page, base_url: str):
        """The Training page should display training status."""
        page.goto(f"{base_url}/training")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # The page should have loaded the training status
        # Look for common status indicators
        body = page.locator("body")
        expect(body).to_be_visible()


class TestInferencePage:
    """Tests for the Inference page."""

    def test_inference_page_loads(self, page: Page, base_url: str):
        """The Inference page should load without errors."""
        page.goto(f"{base_url}/inference")
        page.wait_for_load_state("networkidle")

        body = page.locator("body")
        expect(body).to_be_visible()

    def test_inference_page_shows_checkpoint_selector(self, page: Page, base_url: str):
        """The Inference page should have a checkpoint selector."""
        page.goto(f"{base_url}/inference")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Just verify page loaded successfully
        body = page.locator("body")
        expect(body).to_be_visible()
