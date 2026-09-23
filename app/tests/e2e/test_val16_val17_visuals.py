"""Current-revision desktop evidence for the Training, Inference, and Settings pages."""

from pathlib import Path
import re
from uuid import uuid4

from playwright.sync_api import Page, expect


QA_ROOT = Path(__file__).resolve().parents[3] / "assets" / "QA"


###############################################################################
def _capture(page: Page, name: str) -> None:
    QA_ROOT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(QA_ROOT / name), full_page=False)


###############################################################################
def _assert_supported_desktop(page: Page, width: int, height: int) -> None:
    metrics = page.evaluate(
        """() => ({
            width: window.innerWidth,
            height: window.innerHeight,
            horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
        })"""
    )
    assert metrics == {
        "width": width,
        "height": height,
        "horizontalOverflow": False,
    }
    expect(page.locator(".desktop-size-notice")).to_be_hidden()


###############################################################################
def test_desktop_page_views_and_minimum_width_boundary(page: Page, base_url: str):
    """Capture all principal pages at both supported desktop sizes and the 1099px gate."""
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

    routes = (
        (
            "training",
            "Training Monitor",
            "val17-training",
            (
                ("button", "Use generator"),
                ("heading", "Checkpoints"),
            ),
        ),
        (
            "inference",
            "Session History",
            "val17-inference",
            (
                ("combobox", "Model checkpoint"),
                ("combobox", "Inference dataset"),
            ),
        ),
        (
            "settings",
            "Roulette numbers",
            "val17-settings",
            (
                ("spinbutton", "Minimum"),
                ("spinbutton", "Maximum"),
                ("button", "Save settings"),
            ),
        ),
    )

    for width, height in ((1440, 900), (1100, 800)):
        page.set_viewport_size({"width": width, "height": height})
        for route, heading, image_prefix, controls in routes:
            page.goto(f"{base_url}/{route}")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
            for role, name in controls:
                expect(page.get_by_role(role, name=name, exact=True)).to_be_visible()
            if route == "inference":
                expect(page.get_by_text("AI Suggestion", exact=False)).to_be_visible()
            _assert_supported_desktop(page, width, height)
            _capture(page, f"{image_prefix}-{width}x{height}.png")

    page.set_viewport_size({"width": 1099, "height": 800})
    page.goto(f"{base_url}/inference")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Session History", exact=True)).to_be_visible()
    notice = page.locator(".desktop-size-notice")
    expect(notice).to_be_visible()
    expect(notice).to_contain_text("at least 1100px wide")
    boundary = page.evaluate(
        """() => ({
            width: window.innerWidth,
            mainWidth: document.querySelector('.main-layout').getBoundingClientRect().width,
            columns: getComputedStyle(document.querySelector('.inference-workspace > div'))
                .gridTemplateColumns.trim().split(/\\s+/).length,
        })"""
    )
    assert boundary["width"] == 1099
    assert abs(boundary["mainWidth"] - 1100) < 1
    assert boundary["columns"] == 2
    _capture(page, "val17-inference-minimum-boundary-1099x800.png")

    assert page_errors == []
    assert console_errors == []
    assert failed_requests == []
    assert failed_responses == []


###############################################################################
def test_training_setup_and_active_monitor_render(page: Page, base_url: str):
    """Exercise the stored-dataset wizard and capture a real active training monitor."""
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

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{base_url}/training")
    page.wait_for_load_state("networkidle")

    configure_buttons = page.get_by_role(
        "button", name="Configure training with this dataset", exact=True
    )
    expect(configure_buttons).to_have_count(5)
    configure_buttons.nth(4).click()
    wizard = page.get_by_role("dialog", name="New Training Wizard")
    expect(wizard).to_be_visible()
    wizard_position = wizard.evaluate(
        """dialog => {
            const rect = dialog.getBoundingClientRect();
            return {
                portaledToBody: dialog.parentElement?.parentElement === document.body,
                top: rect.top,
                bottom: rect.bottom,
                viewportHeight: window.innerHeight,
            };
        }"""
    )
    assert wizard_position["portaledToBody"]
    assert wizard_position["top"] >= 0
    assert wizard_position["bottom"] <= wizard_position["viewportHeight"]
    _capture(page, "val17-training-setup-1440x900.png")

    wizard.locator('input[name="perceptiveField"]').fill("8")
    for _ in range(5):
        wizard.get_by_role("button", name="Next", exact=True).click()
    checkpoint = f"val16_visual_{uuid4().hex[:10]}"
    wizard.locator('input[name="checkpointName"]').fill(checkpoint)
    expect(wizard.get_by_text("Episodes", exact=True)).to_be_visible()
    expect(wizard.get_by_text("Use GPU", exact=True)).to_be_visible()
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    wizard.evaluate(
        """dialog => {
            dialog.scrollTop = 0;
            dialog.querySelectorAll('*').forEach(element => { element.scrollTop = 0; });
        }"""
    )
    _capture(page, "val17-training-summary-1440x900.png")

    try:
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/training/start"),
            timeout=60_000,
        ) as start_info:
            wizard.get_by_role("button", name="Confirm", exact=True).click()
        start_response = start_info.value
        assert start_response.status == 202, start_response.text()

        stop_button = page.get_by_role("button", name="Stop", exact=True)
        expect(stop_button).to_be_enabled(timeout=30_000)
        page.wait_for_function(
            """() => /Episode\\s+\\d+\\s+\\/\\s+\\d+\\s+·\\s+Step\\s+[1-9]\\d*/
                .test(document.body.innerText)""",
            timeout=15_000,
        )
        page.get_by_role("heading", name="Training Monitor", exact=True).evaluate(
            "element => element.scrollIntoView({block: 'start', behavior: 'instant'})"
        )
        _capture(page, "val17-training-active-1440x900.png")
    finally:
        stop_button = page.get_by_role("button", name="Stop", exact=True)
        if stop_button.count() and stop_button.is_enabled():
            stop_button.click()
            expect(page.get_by_text("Training cancelled", exact=True)).to_be_visible(
                timeout=45_000
            )

    assert page_errors == []
    assert console_errors == []
    assert failed_requests == []
    assert failed_responses == []


###############################################################################
def test_inference_active_session_render(page: Page, base_url: str):
    """Capture a live checkpoint-backed prediction and return the isolated app to idle."""
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

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{base_url}/inference")
    page.wait_for_load_state("networkidle")
    page.locator("#inference-checkpoint").select_option("val00_lineage_20260921")
    page.locator("#inference-dataset").select_option("5")
    page.locator("#inference-initial-capital").fill("100")
    page.locator("#inference-bet-amount").fill("1")

    try:
        stop_button = page.get_by_role("button", name="Stop", exact=True)
        if stop_button.is_enabled():
            stop_button.click()
            expect(page.get_by_role("button", name="Play", exact=True)).to_be_enabled(
                timeout=15_000
            )

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/inference/sessions/start"),
            timeout=60_000,
        ) as start_info:
            page.get_by_role("button", name="Play", exact=True).click()
        start_response = start_info.value
        assert start_response.status == 200, start_response.text()
        rows = page.locator("table").get_by_role("row")
        expect(rows).to_have_count(2)
        prediction_text = rows.nth(1).get_by_role("cell").nth(1).inner_text()
        assert re.fullmatch(r"Bet on number \d+", prediction_text)
        expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
        expect(page.get_by_role("heading", name="Session History", exact=True)).to_be_visible()
        _capture(page, "val17-inference-active-1440x900.png")
    finally:
        stop_button = page.get_by_role("button", name="Stop", exact=True)
        if stop_button.count() and stop_button.is_enabled():
            stop_button.click()
            expect(page.get_by_role("button", name="Play", exact=True)).to_be_enabled(
                timeout=15_000
            )

    assert page_errors == []
    assert console_errors == []
    assert failed_requests == []
    assert failed_responses == []
