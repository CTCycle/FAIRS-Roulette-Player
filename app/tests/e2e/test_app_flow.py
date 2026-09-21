"""
E2E tests for UI navigation and page rendering.
Tests basic UI functionality using Playwright browser automation.
"""

import json
import re
from pathlib import Path

from playwright.sync_api import Page, expect

###############################################################################
class TestStartupFlow:
    """Tests the frontend-owned backend startup experience."""

    # -------------------------------------------------------------------------
    def test_loading_screen_recovers_after_transient_health_failures(
        self, page: Page, base_url: str
    ):
        """The frontend remains visible while the backend becomes healthy."""
        health_calls = 0
        document_requests = []
        console_messages = []

        def health_route(route):
            nonlocal health_calls
            health_calls += 1
            if health_calls <= 3:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {"status": "starting", "application": "FAIRS"}
                    ),
                )
                return
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {"status": "ok", "application": "FAIRS", "version": "test"}
                ),
            )

        page.route("**/api/health", health_route)
        page.on(
            "request",
            lambda request: document_requests.append(request)
            if request.resource_type == "document"
            else None,
        )

        def capture_console(message):
            console_messages.append(message)

        page.on("console", capture_console)

        page.goto(f"{base_url}/training")

        expect(page.get_by_test_id("startup-screen")).to_be_visible()
        expect(page.get_by_text("Preparing the table…", exact=True)).to_be_visible()
        expect(page.get_by_test_id("startup-roulette-wheel")).to_be_visible()
        page.screenshot(
            path=str(
                Path(__file__).resolve().parents[3]
                / "assets"
                / "QA"
                / "fairs_startup_loading.png"
            ),
            full_page=True,
        )

        expect(
            page.get_by_role("heading", name=re.compile("Training Monitor", re.IGNORECASE))
        ).to_be_visible(timeout=10_000)
        assert health_calls >= 4
        assert len(document_requests) == 1
        assert not [message for message in console_messages if message.type == "error"]

    # -------------------------------------------------------------------------
    def test_already_healthy_backend_skips_visible_startup_delay(
        self, page: Page, base_url: str
    ):
        """A healthy backend transitions directly into the normal application."""

        def health_route(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {"status": "ok", "application": "FAIRS", "version": "test"}
                ),
            )

        page.route("**/api/health", health_route)
        page.goto(base_url)

        expect(page.get_by_role("link", name=re.compile("Training", re.IGNORECASE))).to_be_visible()
        expect(page.get_by_test_id("startup-screen")).to_have_count(0)

    # -------------------------------------------------------------------------
    def test_startup_failure_can_retry_without_reloading_the_document(
        self, page: Page, base_url: str
    ):
        """A timed-out startup shows a safe retry state and recovers in place."""
        backend_available = False
        document_requests = []

        def health_route(route):
            if not backend_available:
                route.abort()
                return
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {"status": "ok", "application": "FAIRS", "version": "test"}
                ),
            )

        page.route("**/api/health", health_route)
        page.on(
            "request",
            lambda request: document_requests.append(request)
            if request.resource_type == "document"
            else None,
        )
        page.clock.install()
        page.goto(base_url)
        expect(page.get_by_test_id("startup-screen")).to_be_visible()

        page.clock.run_for(61_000)

        expect(page.get_by_text("The table is taking a break.", exact=True)).to_be_visible()
        expect(page.get_by_test_id("startup-retry")).to_be_visible()
        expect(page.get_by_text("ERR_CONNECTION_REFUSED", exact=False)).to_have_count(0)

        backend_available = True
        page.get_by_test_id("startup-retry").click()
        page.clock.run_for(3_000)

        expect(page.get_by_role("link", name=re.compile("Training", re.IGNORECASE))).to_be_visible()
        assert len(document_requests) == 1

    # -------------------------------------------------------------------------
    def test_reload_during_startup_restarts_only_health_polling(
        self, page: Page, base_url: str
    ):
        """Reloading during startup keeps the loading experience deterministic."""
        allow_health = False

        def health_route(route):
            if not allow_health:
                route.abort()
                return
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {"status": "ok", "application": "FAIRS", "version": "test"}
                ),
            )

        page.route("**/api/health", health_route)
        page.goto(base_url)
        expect(page.get_by_test_id("startup-screen")).to_be_visible()

        page.reload()
        expect(page.get_by_test_id("startup-screen")).to_be_visible()

        allow_health = True
        expect(page.get_by_role("link", name=re.compile("Training", re.IGNORECASE))).to_be_visible(
            timeout=10_000
        )

    # -------------------------------------------------------------------------
    def test_loading_screen_fits_supported_viewports(self, page: Page, base_url: str):
        """The startup composition stays contained at supported desktop sizes."""

        def health_route(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"status": "starting", "application": "FAIRS"}),
            )

        page.route("**/api/health", health_route)
        qa_root = Path(__file__).resolve().parents[3] / "assets" / "QA"

        for width, height in ((1440, 900), (1100, 800)):
            page.set_viewport_size({"width": width, "height": height})
            page.goto(base_url)
            expect(page.get_by_test_id("startup-screen")).to_be_visible()

            overflow = page.evaluate(
                """() => ({
                    horizontal: document.documentElement.scrollWidth > window.innerWidth,
                    vertical: document.documentElement.scrollHeight > window.innerHeight,
                })"""
            )
            assert overflow == {"horizontal": False, "vertical": False}
            page.screenshot(
                path=str(qa_root / f"fairs_startup_loading_{width}x{height}.png"),
                full_page=True,
            )

###############################################################################
class TestHomePage:
    """Tests for the home page and basic navigation."""

    # -------------------------------------------------------------------------
    def test_homepage_loads_successfully(self, page: Page, base_url: str):
        """The homepage should load without errors."""
        page.goto(base_url)
        expect(page).to_have_title(re.compile("FAIRS Roulette Player", re.IGNORECASE))

    # -------------------------------------------------------------------------
    def test_homepage_has_navigation(self, page: Page, base_url: str):
        """The homepage should have navigation elements."""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("Training", exact=False).first).to_be_visible()
        expect(page.get_by_text("Inference", exact=False).first).to_be_visible()

###############################################################################
class TestNavigationFlow:
    """Tests for navigating between different pages."""

    # -------------------------------------------------------------------------
    def test_navigate_to_training_page(self, page: Page, base_url: str):
        """Should be able to navigate to the Training page."""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")

        # Try to find and click the Training link
        training_link = page.get_by_role(
            "link", name=re.compile("Training", re.IGNORECASE)
        )
        expect(training_link).to_be_visible()
        training_link.click()

        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(re.compile(".*training.*", re.IGNORECASE))

    # -------------------------------------------------------------------------
    def test_navigate_to_inference_page(self, page: Page, base_url: str):
        """Should be able to navigate to the Inference page."""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")

        # Try to find and click the Inference link
        inference_link = page.get_by_role(
            "link", name=re.compile("Inference", re.IGNORECASE)
        )
        expect(inference_link).to_be_visible()
        inference_link.click()

        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(re.compile(".*inference.*", re.IGNORECASE))

###############################################################################
class TestTrainingPage:
    """Tests for the Training page."""

    # -------------------------------------------------------------------------
    def test_training_page_loads(self, page: Page, base_url: str):
        """The Training page should load without errors."""
        page.goto(f"{base_url}/training")
        page.wait_for_load_state("networkidle")

        expect(
            page.get_by_role(
                "heading", name=re.compile("Training Monitor", re.IGNORECASE)
            )
        ).to_be_visible()
        expect(page.locator(".metric-group")).to_have_count(3)
        expect(page.locator(".metric-item")).to_have_count(13)
        expect(page.locator(".metric-card")).to_have_count(0)
        expect(page.get_by_text("Checkpoints", exact=False).first).to_be_visible()

###############################################################################
class TestInferencePage:
    """Tests for the Inference page."""

    # -------------------------------------------------------------------------
    def test_inference_page_loads(self, page: Page, base_url: str):
        """The Inference page should load without errors."""
        page.goto(f"{base_url}/inference")
        page.wait_for_load_state("networkidle")

        expect(
            page.get_by_role(
                "heading", name=re.compile("Session History", re.IGNORECASE)
            )
        ).to_be_visible()
        expect(
            page.get_by_text(
                "Pair a trained checkpoint with a dataset, step through predictions, and inspect session history in real time.",
                exact=True,
            )
        ).to_have_count(0)
        expect(page.get_by_text("AI Suggestion", exact=False)).to_be_visible()

    # -------------------------------------------------------------------------
    def test_inference_page_shows_checkpoint_selector(self, page: Page, base_url: str):
        """The Inference page should have a checkpoint selector."""
        page.goto(f"{base_url}/inference")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("Select checkpoint", exact=False)).to_be_visible()
        expect(page.get_by_text("Selected dataset", exact=False)).to_be_visible()
