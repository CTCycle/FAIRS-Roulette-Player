"""
E2E tests for UI navigation and page rendering.
Tests basic UI functionality using Playwright browser automation.
"""

import json
import re
import sqlite3
from pathlib import Path

from playwright.sync_api import APIRequestContext, Page, expect

from server.common import path as shared_paths

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
        zero_slice_background = page.get_by_test_id("startup-wheel-rotor").evaluate(
            "element => getComputedStyle(element).backgroundImage"
        )
        assert "conic-gradient" in zero_slice_background
        assert "rgb(34, 197, 94)" in zero_slice_background
        assert page.locator(".startup-wheel__zero-pocket").count() == 0
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
class TestCheckpointHandoff:
    """Browser evidence for checkpoint provenance handoff boundaries."""

    # -------------------------------------------------------------------------
    def test_open_in_inference_preserves_checkpoint_provenance(
        self, page: Page, base_url: str
    ) -> None:
        page_errors: list[str] = []
        console_errors: list[str] = []
        failed_requests: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )

        page.goto(f"{base_url}/training")
        page.wait_for_load_state("networkidle")
        checkpoint_row = page.locator(".preview-row").filter(
            has_text="val00_lineage_20260921"
        )
        expect(checkpoint_row).to_be_visible()
        checkpoint_row.get_by_title(
            "Open checkpoint in Inference using its training dataset"
        ).click()

        expect(page).to_have_url(re.compile(r".*/inference$"))
        expect(page.locator("#inference-checkpoint")).to_have_value(
            "val00_lineage_20260921"
        )
        expect(page.locator("#inference-dataset")).to_have_value("5")
        expect(page.locator("#inference-initial-capital")).to_have_value("1000")
        expect(page.locator("#inference-bet-amount")).to_have_value("10")
        assert page_errors == []
        assert console_errors == []
        assert failed_requests == []

    # -------------------------------------------------------------------------
    def test_missing_checkpoint_dataset_requires_explicit_selection(
        self, page: Page, base_url: str
    ) -> None:
        page.route(
            "**/api/training/checkpoints/val00_lineage_20260921/metadata",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "checkpoint": "val00_lineage_20260921",
                        "summary": {
                            "dataset_id": 999999,
                            "sample_size": 1.0,
                            "seed": 42,
                            "episodes": 1,
                            "batch_size": 1,
                            "learning_rate": 0.0001,
                            "perceptive_field_size": 8,
                            "qnet_neurons": 8,
                            "embedding_dimensions": 8,
                            "exploration_rate": 0.75,
                            "exploration_rate_decay": 0.995,
                            "discount_rate": 0.5,
                            "model_update_frequency": 10,
                            "bet_amount": 10,
                            "initial_capital": 1000,
                            "final_loss": 1.0,
                            "final_rmse": 1.0,
                            "final_val_loss": None,
                            "final_val_rmse": None,
                        },
                    }
                ),
            ),
        )
        page.goto(f"{base_url}/training")
        page.wait_for_load_state("networkidle")
        checkpoint_row = page.locator(".preview-row").filter(
            has_text="val00_lineage_20260921"
        )
        expect(checkpoint_row).to_be_visible()
        checkpoint_row.get_by_title(
            "Open checkpoint in Inference using its training dataset"
        ).click()

        expect(page).to_have_url(re.compile(r".*/training$"))
        expect(page.locator(".preview-error")).to_contain_text(
            "choose a dataset explicitly instead of substituting one automatically"
        )

###############################################################################
def _open_stored_training_wizard(page: Page, base_url: str):
    page.goto(f"{base_url}/training")
    page.wait_for_load_state("networkidle")
    dataset_row = page.locator(".preview-row").filter(has_text="val00_training_lineage")
    expect(dataset_row).to_contain_text("120 rows")
    dataset_row.get_by_role(
        "button", name="Configure training with this dataset", exact=True
    ).click()
    modal = page.get_by_role("dialog")
    expect(modal).to_be_visible()
    return modal


###############################################################################
class TestTrainingWizardFlow:
    """Browser coverage for the six-step training configuration boundary."""

    # -------------------------------------------------------------------------
    def test_stored_dataset_wizard_navigation_state_and_summary(
        self, page: Page, base_url: str
    ) -> None:
        page_errors: list[str] = []
        console_errors: list[str] = []
        failed_requests: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )

        modal = _open_stored_training_wizard(page, base_url)
        expect(modal.locator(".wizard-breadcrumb")).to_have_count(6)
        expect(modal.locator(".wizard-modal-subtitle")).to_contain_text(
            "Dataset: val00_training_lineage"
        )

        perceptive_field = modal.locator('input[name="perceptiveField"]')
        perceptive_field.fill("8")
        modal.get_by_role("button", name="Next", exact=True).click()

        max_memory = modal.locator('input[name="maxMemorySize"]')
        replay_buffer = modal.locator('input[name="replayBufferSize"]')
        max_memory.fill("100")
        replay_buffer.fill("100")
        modal.get_by_role("button", name="Previous", exact=True).click()
        expect(perceptive_field).to_have_value("8")
        modal.get_by_role("button", name="Next", exact=True).click()
        expect(max_memory).to_have_value("100")
        expect(replay_buffer).to_have_value("100")
        modal.get_by_role("button", name="Next", exact=True).click()

        dynamic_betting = modal.locator('input[name="dynamicBettingEnabled"]')
        strategy_model = modal.locator('input[name="betStrategyModelEnabled"]')
        fixed_strategy = modal.locator('select[name="betStrategyFixedId"]')
        bet_unit_toggle = modal.locator('input[name="betUnitEnabled"]')
        bet_unit = modal.locator('input[name="betUnit"]')
        bet_max_toggle = modal.locator('input[name="betMaxEnabled"]')
        bet_max = modal.locator('input[name="betMax"]')

        expect(strategy_model).to_be_disabled()
        expect(fixed_strategy).to_be_disabled()
        expect(bet_unit_toggle).to_be_disabled()
        expect(bet_unit).to_be_disabled()
        expect(bet_max_toggle).to_be_disabled()
        expect(bet_max).to_be_disabled()

        dynamic_betting.check()
        expect(strategy_model).to_be_enabled()
        expect(fixed_strategy).to_be_enabled()
        expect(bet_unit_toggle).to_be_enabled()
        expect(bet_max_toggle).to_be_enabled()
        strategy_model.check()
        expect(fixed_strategy).to_be_disabled()
        strategy_model.uncheck()
        fixed_strategy.select_option("2")
        bet_unit_toggle.check()
        bet_max_toggle.check()
        bet_unit.fill("5")
        bet_max.fill("20")
        modal.get_by_role("button", name="Next", exact=True).click()

        expect(modal.locator('input[type="range"]')).to_have_count(2)
        modal.locator('input[name="splitSeed"]').fill("123")
        modal.get_by_role("button", name="Next", exact=True).click()

        episodes = modal.locator('input[name="episodes"]')
        max_steps = modal.locator('input[name="maxStepsEpisode"]')
        batch_size = modal.locator('input[name="batchSize"]')
        training_seed = modal.locator('input[name="trainingSeed"]')
        episodes.fill("1")
        max_steps.fill("100")
        batch_size.fill("100")
        training_seed.fill("2026")
        device_gpu = modal.locator('input[name="deviceGPU"]')
        mixed_precision = modal.locator('input[name="useMixedPrecision"]')
        expect(device_gpu).to_be_enabled()
        expect(mixed_precision).to_be_enabled()
        device_gpu.check()
        device_gpu.uncheck()
        mixed_precision.check()
        mixed_precision.uncheck()
        modal.get_by_role("button", name="Next", exact=True).click()

        summary = modal.locator(".wizard-summary")

        def assert_summary_value(label: str, value: str) -> None:
            row = summary.locator(".wizard-summary-row").filter(has_text=label)
            expect(row).to_contain_text(value)

        assert_summary_value("Dataset", "val00_training_lineage")
        assert_summary_value("Perceptive Field", "8")
        assert_summary_value("Max Memory", "100")
        assert_summary_value("Replay Buffer", "100")
        assert_summary_value("Dynamic Betting", "Enabled")
        assert_summary_value("Strategy Model", "Disabled")
        assert_summary_value("Fixed Strategy", "Reverse")
        assert_summary_value("Bet Unit", "5")
        assert_summary_value("Bet Max", "20")
        assert_summary_value("Split Seed", "123")
        assert_summary_value("Episodes", "1")
        assert_summary_value("Max Steps", "100")
        assert_summary_value("Batch Size", "100")
        assert_summary_value("Training Seed", "2026")
        assert_summary_value("Use GPU", "No")
        assert_summary_value("Mixed Precision", "No")

        modal.get_by_role("button", name=re.compile(r"^1\s+Agent Configuration")).click()
        expect(perceptive_field).to_have_value("8")
        modal.get_by_role("button", name=re.compile(r"^6\s+Summary")).click()
        expect(summary.locator(".wizard-summary-row").filter(has_text="Batch Size")).to_contain_text(
            "100"
        )
        modal.get_by_role("button", name="Cancel", exact=True).click()

        page_errors_seen = page_errors[:]
        console_errors_seen = console_errors[:]
        assert page_errors_seen == []
        assert console_errors_seen == []
        assert failed_requests == []

    # -------------------------------------------------------------------------
    def test_generator_entry_has_distinct_mode_and_summary_values(
        self, page: Page, base_url: str
    ) -> None:
        page.goto(f"{base_url}/training")
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Use generator", exact=True).click()
        modal = page.get_by_role("dialog")
        expect(modal.locator(".wizard-modal-subtitle")).to_contain_text(
            "Mode: Synthetic Generator"
        )

        modal.get_by_role("button", name=re.compile(r"^4\s+Dataset Configuration")).click()
        expect(modal.locator(".wizard-step-title")).to_have_text("Generator Parameters")
        generated_samples = modal.locator('input[name="numGeneratedSamples"]')
        generated_samples.fill("200")
        modal.get_by_role("button", name=re.compile(r"^6\s+Summary")).click()
        summary = modal.locator(".wizard-summary")
        expect(summary.locator(".wizard-summary-row").filter(has_text="Dataset")).to_contain_text(
            "Synthetic Data"
        )
        expect(
            summary.locator(".wizard-summary-row").filter(has_text="Generated Samples")
        ).to_contain_text("200")
        modal.get_by_role("button", name="Cancel", exact=True).click()

    # -------------------------------------------------------------------------
    def test_invalid_semantic_configuration_stays_open_and_never_starts(
        self, page: Page, base_url: str
    ) -> None:
        start_requests: list[str] = []
        page.on(
            "request",
            lambda request: start_requests.append(request.url)
            if request.method == "POST" and request.url.endswith("/api/training/start")
            else None,
        )
        modal = _open_stored_training_wizard(page, base_url)
        modal.locator('input[name="explorationRate"]').fill("0.2")
        modal.locator('input[name="minExplorationRate"]').fill("0.5")
        modal.get_by_role("button", name=re.compile(r"^6\s+Summary")).click()
        modal.get_by_role("button", name="Confirm", exact=True).click()

        expect(modal).to_be_visible()
        expect(modal.locator(".wizard-error")).to_contain_text(
            "minimum_exploration_rate"
        )
        assert start_requests == []

    # -------------------------------------------------------------------------
    def test_missing_required_numeric_value_is_rejected_before_start(
        self, page: Page, base_url: str
    ) -> None:
        request_order: list[str] = []
        page.on(
            "request",
            lambda request: request_order.append("validate")
            if request.method == "POST"
            and request.url.endswith("/api/training/validate")
            else request_order.append("start")
            if request.method == "POST"
            and request.url.endswith("/api/training/start")
            else None,
        )
        modal = _open_stored_training_wizard(page, base_url)
        modal.get_by_role("button", name=re.compile(r"^5\s+Session")).click()
        modal.locator('input[name="episodes"]').fill("")
        modal.get_by_role("button", name=re.compile(r"^6\s+Summary")).click()

        with page.expect_response("**/api/training/validate") as validation_response:
            modal.get_by_role("button", name="Confirm", exact=True).click()

        assert validation_response.value.status == 422
        expect(modal).to_be_visible()
        expect(modal.locator(".wizard-error")).to_contain_text("episodes")
        assert request_order == ["validate"]

    # -------------------------------------------------------------------------
    def test_valid_configuration_orders_validate_then_start_with_validated_payload(
        self, page: Page, base_url: str
    ) -> None:
        request_order: list[str] = []
        page.on(
            "request",
            lambda request: request_order.append("validate")
            if request.method == "POST" and request.url.endswith("/api/training/validate")
            else request_order.append("start")
            if request.method == "POST" and request.url.endswith("/api/training/start")
            else None,
        )

        def fulfill_start(route) -> None:
            route.fulfill(
                status=202,
                content_type="application/json",
                body=json.dumps(
                    {
                        "job_id": "browser-wizard-order-test",
                        "job_type": "training",
                        "status": "started",
                        "message": "Training started.",
                        "poll_interval": 1.0,
                    }
                ),
            )

        page.route("**/api/training/start", fulfill_start)
        modal = _open_stored_training_wizard(page, base_url)
        modal.get_by_role("button", name=re.compile(r"^6\s+Summary")).click()
        modal.locator('input[name="checkpointName"]').fill("browser_order_check")

        with page.expect_response("**/api/training/validate") as validation_response_info:
            with page.expect_request("**/api/training/start") as start_request_info:
                modal.get_by_role("button", name="Confirm", exact=True).click()

        validation_payload = validation_response_info.value.json()
        start_payload = json.loads(start_request_info.value.post_data or "{}")
        expect(modal).not_to_be_visible()
        assert request_order == ["validate", "start"]
        assert validation_payload == start_payload
        assert start_payload["dataset_id"] == 5
        assert start_payload["use_data_generator"] is False

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

    # -------------------------------------------------------------------------
    def test_history_correction_and_removal_replay_persisted_session(
        self,
        page: Page,
        base_url: str,
        api_context: APIRequestContext,
    ) -> None:
        """History edits replace the live session and persist the replayed rows."""
        page_errors: list[str] = []
        console_errors: list[str] = []
        failed_requests: list[str] = []
        failed_responses: list[str] = []
        created_session_ids: list[str] = []

        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )
        page.on(
            "response",
            lambda response: failed_responses.append(
                f"{response.status} {response.url}"
            )
            if response.status >= 400
            else None,
        )

        def is_session_start(response) -> bool:
            return (
                response.request.method == "POST"
                and response.url.endswith("/api/inference/sessions/start")
            )

        def session_snapshot(session_id: str) -> dict:
            response = api_context.get(
                f"/api/inference/sessions/{session_id}"
            )
            assert response.status == 200, (
                f"Expected session snapshot 200, got {response.status}: "
                f"{response.text()}"
            )
            return response.json()

        def assert_session_closed(session_id: str) -> None:
            response = api_context.post(
                f"/api/inference/sessions/{session_id}/next"
            )
            assert response.status == 404, (
                f"Expected closed session 404, got {response.status}: "
                f"{response.text()}"
            )

        def assert_ui_step_matches_snapshot(row, step: dict) -> None:
            cells = row.get_by_role("cell")
            assert int(cells.nth(3).inner_text().replace("+", "")) == step["reward"]
            assert float(cells.nth(4).inner_text()) == step["capital_after"]

        page.set_viewport_size({"width": 1440, "height": 900})
        try:
            page.goto(f"{base_url}/inference")
            page.wait_for_load_state("networkidle")
            page.locator("#inference-checkpoint").select_option(
                "val00_lineage_20260921"
            )
            page.locator("#inference-dataset").select_option("5")
            page.locator("#inference-initial-capital").fill("1000")
            page.locator("#inference-bet-amount").fill("10")

            with page.expect_response(is_session_start, timeout=60_000) as start_info:
                page.get_by_role("button", name="Play", exact=True).click()
            start_response = start_info.value
            assert start_response.status == 200, start_response.text()
            current_session_id = str(start_response.json()["session_id"])
            created_session_ids.append(current_session_id)

            rows = page.locator("table").get_by_role("row")
            expect(rows).to_have_count(2)
            first_row = rows.nth(1)
            prediction_text = first_row.get_by_role("cell").nth(1).inner_text()
            prediction_match = re.search(r"Bet on number (\d+)", prediction_text)
            assert prediction_match is not None, prediction_text
            predicted_number = int(prediction_match.group(1))
            original_outcome = (predicted_number + 1) % 37

            first_field = page.get_by_label("Observed value for step 1")
            first_field.fill(str(original_outcome))
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith(
                    f"/api/inference/sessions/{current_session_id}/step"
                )
            ) as first_step_info:
                first_row.get_by_role(
                    "button", name="Confirm observed"
                ).click()
            assert first_step_info.value.status == 200
            expect(first_field).to_be_disabled()
            original_first_reward = int(
                first_row.get_by_role("cell").nth(3).inner_text().replace("+", "")
            )
            first_row.get_by_role("button", name="Next prediction").click()

            expect(rows).to_have_count(3)
            second_row = rows.nth(2)
            second_prediction_text = (
                second_row.get_by_role("cell").nth(1).inner_text()
            )
            second_prediction_match = re.search(
                r"Bet on number (\d+)", second_prediction_text
            )
            assert second_prediction_match is not None, second_prediction_text
            second_predicted_number = int(second_prediction_match.group(1))
            second_outcome = (second_predicted_number + 1) % 37
            second_field = page.get_by_label("Observed value for step 2")
            second_field.fill(str(second_outcome))
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith(
                    f"/api/inference/sessions/{current_session_id}/step"
                )
            ) as second_step_info:
                second_row.get_by_role(
                    "button", name="Confirm observed"
                ).click()
            assert second_step_info.value.status == 200
            expect(second_field).to_be_disabled()
            second_row.get_by_role("button", name="Next prediction").click()
            expect(rows).to_have_count(4)

            before_edit_snapshot = session_snapshot(current_session_id)
            assert before_edit_snapshot["step_count"] == 2
            assert before_edit_snapshot["prediction_pending"] is True
            assert len(before_edit_snapshot["steps"]) == 3
            assert before_edit_snapshot["steps"][0]["reward"] == original_first_reward

            first_row = rows.nth(1)
            first_row.get_by_role("button", name="Modify observed").click()
            first_field = page.get_by_label("Observed value for step 1")
            first_field.fill(str(predicted_number))
            with page.expect_response(is_session_start, timeout=60_000) as correction_info:
                first_row.get_by_role(
                    "button", name="Confirm observed"
                ).click()
            correction_response = correction_info.value
            assert correction_response.status == 200, correction_response.text()
            correction_request = correction_response.request
            assert (
                correction_request.headers.get("x-preserve-inference-session")
                == current_session_id
            )
            previous_session_id = current_session_id
            current_session_id = str(correction_response.json()["session_id"])
            created_session_ids.append(current_session_id)

            expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
            expect(rows).to_have_count(4)
            assert_session_closed(previous_session_id)
            corrected_snapshot = session_snapshot(current_session_id)
            corrected_steps = corrected_snapshot["steps"]
            assert corrected_snapshot["step_count"] == 2
            assert corrected_snapshot["prediction_pending"] is True
            assert len(corrected_steps) == 3
            assert [step["observed_outcome_id"] for step in corrected_steps] == [
                predicted_number,
                second_outcome,
                None,
            ]
            assert corrected_steps[0]["reward"] != original_first_reward
            assert corrected_snapshot["current_capital"] == corrected_steps[1][
                "capital_after"
            ]
            first_row = rows.nth(1)
            second_row = rows.nth(2)
            expect(page.get_by_label("Observed value for step 1")).to_have_value(
                str(predicted_number)
            )
            expect(page.get_by_label("Observed value for step 2")).to_have_value(
                str(second_outcome)
            )
            assert_ui_step_matches_snapshot(first_row, corrected_steps[0])
            assert_ui_step_matches_snapshot(second_row, corrected_steps[1])
            assert page.get_by_label("Observed value for step 3").input_value() == ""
            assert_session_closed(previous_session_id)

            with page.expect_response(is_session_start, timeout=60_000) as removal_info:
                second_row.get_by_role("button", name="Remove row").click()
            removal_response = removal_info.value
            assert removal_response.status == 200, removal_response.text()
            assert (
                removal_response.request.headers.get("x-preserve-inference-session")
                == current_session_id
            )
            previous_session_id = current_session_id
            current_session_id = str(removal_response.json()["session_id"])
            created_session_ids.append(current_session_id)
            expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
            expect(rows).to_have_count(3)
            assert_session_closed(previous_session_id)
            final_snapshot = session_snapshot(current_session_id)
            final_steps = final_snapshot["steps"]
            assert final_snapshot["step_count"] == 1
            assert final_snapshot["prediction_pending"] is True
            assert len(final_steps) == 2
            assert [step["observed_outcome_id"] for step in final_steps] == [
                predicted_number,
                None,
            ]
            expect(page.get_by_label("Observed value for step 1")).to_have_value(
                str(predicted_number)
            )
            assert page.get_by_label("Observed value for step 2").input_value() == ""
            assert_ui_step_matches_snapshot(rows.nth(1), final_steps[0])
            assert final_snapshot["current_capital"] == final_steps[0]["capital_after"]
            assert page_errors == []
            assert console_errors == []
            assert failed_requests == []
            assert failed_responses == []

            qa_dir = Path(__file__).resolve().parents[3] / "assets" / "QA"
            page.screenshot(
                path=str(qa_dir / "val12-inference-history-replay.png"),
                full_page=True,
            )
        finally:
            # Close sessions but preserve persisted rows as audit evidence.
            for session_id in reversed(created_session_ids):
                api_context.post(
                    f"/api/inference/sessions/{session_id}/shutdown"
                )
                api_context.post(
                    f"/api/inference/sessions/{session_id}/rows/clear"
                )

    # -------------------------------------------------------------------------
    def test_failed_history_replay_keeps_previous_session_active(
        self,
        page: Page,
        base_url: str,
        api_context: APIRequestContext,
    ) -> None:
        """A partial failed replay is closed without replacing the live session."""
        page_errors: list[str] = []
        console_errors: list[str] = []
        failed_requests: list[str] = []
        failed_responses: list[str] = []
        created_session_ids: list[str] = []
        replacement_session_id: str | None = None
        replacement_step_count = 0
        replacement_start_status: int | None = None
        armed = False
        failure_detail = "Injected VAL-13 replay failure."

        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )
        page.on(
            "response",
            lambda response: failed_responses.append(
                f"{response.status} {response.url}"
            )
            if response.status >= 400
            else None,
        )

        def is_session_start(response) -> bool:
            return (
                response.request.method == "POST"
                and response.url.endswith("/api/inference/sessions/start")
            )

        def capture_replacement_start(route) -> None:
            nonlocal replacement_session_id, replacement_start_status
            if not armed:
                route.continue_()
                return

            response = route.fetch()
            replacement_start_status = response.status
            if response.status == 200:
                replacement_session_id = str(response.json()["session_id"])
                created_session_ids.append(replacement_session_id)
            route.fulfill(response=response)

        def fail_second_replay_step(route) -> None:
            nonlocal replacement_step_count
            request_url = route.request.url
            if (
                not armed
                or replacement_session_id is None
                or not request_url.endswith(
                    f"/api/inference/sessions/{replacement_session_id}/step"
                )
            ):
                route.continue_()
                return

            replacement_step_count += 1
            if replacement_step_count == 2:
                route.fulfill(
                    status=503,
                    content_type="application/json",
                    body=json.dumps({"detail": failure_detail}),
                )
                return
            route.continue_()

        page.route("**/api/inference/sessions/start", capture_replacement_start)
        page.route("**/api/inference/sessions/*/step", fail_second_replay_step)

        def session_snapshot(session_id: str) -> dict:
            response = api_context.get(f"/api/inference/sessions/{session_id}")
            assert response.status == 200, (
                f"Expected session snapshot 200, got {response.status}: "
                f"{response.text()}"
            )
            return response.json()

        def persisted_session_state(session_id: str) -> tuple[str | None, list[tuple]]:
            with sqlite3.connect(shared_paths.DATABASE_PATH, timeout=20) as connection:
                session_row = connection.execute(
                    "SELECT ended_at FROM inference_sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                steps = connection.execute(
                    "SELECT step_number, observed_outcome_id "
                    "FROM inference_session_steps WHERE session_id = ? "
                    "ORDER BY step_number",
                    (session_id,),
                ).fetchall()
            assert session_row is not None, f"Missing persisted session {session_id}"
            return session_row[0], steps

        def assert_session_closed(session_id: str) -> None:
            response = api_context.post(
                f"/api/inference/sessions/{session_id}/next"
            )
            assert response.status == 404, (
                f"Expected closed session 404, got {response.status}: "
                f"{response.text()}"
            )

        def assert_ui_step_matches_snapshot(row, step: dict) -> None:
            cells = row.get_by_role("cell")
            assert int(cells.nth(3).inner_text().replace("+", "")) == step["reward"]
            assert float(cells.nth(4).inner_text()) == step["capital_after"]

        page.set_viewport_size({"width": 1440, "height": 900})
        try:
            page.goto(f"{base_url}/inference")
            page.wait_for_load_state("networkidle")
            page.locator("#inference-checkpoint").select_option(
                "val00_lineage_20260921"
            )
            page.locator("#inference-dataset").select_option("5")
            page.locator("#inference-initial-capital").fill("1000")
            page.locator("#inference-bet-amount").fill("10")

            with page.expect_response(is_session_start, timeout=60_000) as start_info:
                page.get_by_role("button", name="Play", exact=True).click()
            start_response = start_info.value
            assert start_response.status == 200, start_response.text()
            existing_session_id = str(start_response.json()["session_id"])
            created_session_ids.append(existing_session_id)

            rows = page.locator("table").get_by_role("row")
            expect(rows).to_have_count(2)
            first_row = rows.nth(1)
            prediction_text = first_row.get_by_role("cell").nth(1).inner_text()
            prediction_match = re.search(r"Bet on number (\d+)", prediction_text)
            assert prediction_match is not None, prediction_text
            predicted_number = int(prediction_match.group(1))
            original_outcome = (predicted_number + 1) % 37

            first_field = page.get_by_label("Observed value for step 1")
            first_field.fill(str(original_outcome))
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith(
                    f"/api/inference/sessions/{existing_session_id}/step"
                )
            ) as first_step_info:
                first_row.get_by_role(
                    "button", name="Confirm observed"
                ).click()
            assert first_step_info.value.status == 200
            first_row.get_by_role("button", name="Next prediction").click()

            expect(rows).to_have_count(3)
            second_row = rows.nth(2)
            second_prediction_text = second_row.get_by_role("cell").nth(1).inner_text()
            second_prediction_match = re.search(
                r"Bet on number (\d+)", second_prediction_text
            )
            assert second_prediction_match is not None, second_prediction_text
            second_predicted_number = int(second_prediction_match.group(1))
            second_outcome = (second_predicted_number + 1) % 37
            second_field = page.get_by_label("Observed value for step 2")
            second_field.fill(str(second_outcome))
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith(
                    f"/api/inference/sessions/{existing_session_id}/step"
                )
            ) as second_step_info:
                second_row.get_by_role(
                    "button", name="Confirm observed"
                ).click()
            assert second_step_info.value.status == 200
            second_row.get_by_role("button", name="Next prediction").click()
            expect(rows).to_have_count(4)

            before_failure_snapshot = session_snapshot(existing_session_id)
            assert before_failure_snapshot["step_count"] == 2
            assert before_failure_snapshot["prediction_pending"] is True
            assert len(before_failure_snapshot["steps"]) == 3

            first_row = rows.nth(1)
            first_row.get_by_role("button", name="Modify observed").click()
            first_field = page.get_by_label("Observed value for step 1")
            first_field.fill(str(predicted_number))
            armed = True
            with (
                page.expect_response(is_session_start, timeout=60_000) as replacement_info,
                page.expect_response(
                    lambda response: response.status == 503
                    and response.request.method == "POST"
                    and response.url.endswith("/step"),
                    timeout=60_000,
                ) as failure_info,
            ):
                first_row.get_by_role(
                    "button", name="Confirm observed"
                ).click()

            assert replacement_info.value.status == 200
            assert replacement_session_id == str(
                replacement_info.value.json()["session_id"]
            )
            assert (
                replacement_info.value.request.headers.get(
                    "x-preserve-inference-session"
                )
                == existing_session_id
            )
            assert replacement_start_status == 200
            assert replacement_step_count == 2
            assert failure_info.value.status == 503
            assert failure_info.value.url.endswith(
                f"/api/inference/sessions/{replacement_session_id}/step"
            )

            expect(page.get_by_role("alert")).to_have_text(failure_detail)
            expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
            assert session_snapshot(existing_session_id) == before_failure_snapshot
            same_bet_response = api_context.post(
                f"/api/inference/sessions/{existing_session_id}/bet",
                data={"bet_amount": before_failure_snapshot["current_bet"]},
            )
            assert same_bet_response.status == 200, same_bet_response.text()
            assert session_snapshot(existing_session_id) == before_failure_snapshot

            assert replacement_session_id is not None
            assert_session_closed(replacement_session_id)
            existing_ended_at, existing_steps = persisted_session_state(
                existing_session_id
            )
            assert existing_ended_at is None
            assert existing_steps == [
                (1, original_outcome),
                (2, second_outcome),
                (3, None),
            ]
            replacement_ended_at, replacement_steps = persisted_session_state(
                replacement_session_id
            )
            assert replacement_ended_at is not None
            assert replacement_steps == [(1, predicted_number), (2, None)]
            expect(page.get_by_label("Observed value for step 1")).to_have_value(
                str(original_outcome)
            )
            expect(
                rows.nth(1).get_by_role("button", name="Modify observed")
            ).to_be_visible()
            assert_ui_step_matches_snapshot(
                rows.nth(1), before_failure_snapshot["steps"][0]
            )

            qa_dir = Path(__file__).resolve().parents[3] / "assets" / "QA"
            page.screenshot(
                path=str(qa_dir / "val13-inference-replacement-rollback.png"),
                full_page=True,
            )

            page.reload()
            page.wait_for_load_state("networkidle")
            expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
            rows = page.locator("table").get_by_role("row")
            expect(rows).to_have_count(4)
            expect(page.get_by_label("Observed value for step 1")).to_have_value(
                str(original_outcome)
            )
            expect(page.get_by_label("Observed value for step 2")).to_have_value(
                str(second_outcome)
            )
            assert_ui_step_matches_snapshot(rows.nth(1), before_failure_snapshot["steps"][0])
            assert_ui_step_matches_snapshot(rows.nth(2), before_failure_snapshot["steps"][1])
            expect(page.get_by_label("Observed value for step 3")).to_have_value("")
            assert page_errors == []
            assert len(console_errors) == 1
            assert "503 (Service Unavailable)" in console_errors[0]
            assert failed_requests == []
            assert failed_responses == [
                f"503 {failure_info.value.url}"
            ]
        finally:
            for session_id in reversed(created_session_ids):
                api_context.post(
                    f"/api/inference/sessions/{session_id}/shutdown"
                )

###############################################################################
class TestDesktopWindowBoundary:
    """The shared shell keeps its desktop geometry below the supported width."""

    # -------------------------------------------------------------------------
    def test_main_layout_respects_desktop_minimum(
        self, page: Page, base_url: str
    ) -> None:
        page_errors: list[str] = []
        console_errors: list[str] = []
        failed_requests: list[str] = []
        failed_responses: list[str] = []

        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )
        page.on(
            "response",
            lambda response: failed_responses.append(
                f"{response.status} {response.url}"
            )
            if response.status >= 400
            else None,
        )

        page.set_viewport_size({"width": 1100, "height": 800})
        page.goto(f"{base_url}/training")
        page.wait_for_load_state("networkidle")

        expect(
            page.get_by_role("heading", name="Training Monitor", exact=True)
        ).to_be_visible()
        expect(page.locator(".desktop-size-notice")).to_be_hidden()
        supported_metrics = page.evaluate(
            """() => ({
                viewportWidth: window.innerWidth,
                mainWidth: document.querySelector('.main-layout').getBoundingClientRect().width,
                horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
            })"""
        )
        assert supported_metrics["viewportWidth"] == 1100
        assert abs(supported_metrics["mainWidth"] - 1100) < 1
        assert supported_metrics["horizontalOverflow"] is False

        page.set_viewport_size({"width": 1099, "height": 800})
        page.goto(f"{base_url}/inference")
        page.wait_for_load_state("networkidle")

        expect(
            page.get_by_role("heading", name="Session History", exact=True)
        ).to_be_visible()
        notice = page.locator(".desktop-size-notice")
        expect(notice).to_be_visible()
        expect(notice).to_contain_text("at least 1100px wide")
        below_minimum_metrics = page.locator(
            ".inference-workspace > div"
        ).evaluate(
            """root => {
                const panels = Array.from(root.children).map((panel) => {
                    const rect = panel.getBoundingClientRect();
                    return { left: rect.left, top: rect.top };
                });
                return {
                    viewportWidth: window.innerWidth,
                    mainWidth: document.querySelector('.main-layout').getBoundingClientRect().width,
                    noticeDisplay: getComputedStyle(document.querySelector('.desktop-size-notice')).display,
                    gridColumns: getComputedStyle(root).gridTemplateColumns.trim().split(/\\s+/).length,
                    panelTopDelta: Math.abs(panels[0].top - panels[1].top),
                };
            }"""
        )
        assert below_minimum_metrics["viewportWidth"] == 1099
        assert abs(below_minimum_metrics["mainWidth"] - 1100) < 1
        assert below_minimum_metrics["noticeDisplay"] == "flex"
        assert below_minimum_metrics["gridColumns"] == 2
        assert below_minimum_metrics["panelTopDelta"] < 1
        assert page_errors == []
        assert console_errors == []
        assert failed_requests == []
        assert failed_responses == []
