"""Focused browser coverage for the optional in-app guidance system."""

from playwright.sync_api import Page, expect


GUIDANCE_KEY = "fairs.guidance"

###############################################################################
def _assert_tour_keyboard_dismissal(page: Page, title: str) -> None:
    tour = page.get_by_role("dialog", name=title)
    expect(tour).to_be_visible()
    expect(tour).to_have_attribute("aria-modal", "true")
    expect(tour).to_have_attribute("aria-labelledby", "guidance-tour-title")
    expect(tour).to_have_attribute("aria-describedby", "guidance-tour-body")

    close_button = tour.get_by_role("button", name="Close walkthrough")
    next_button = tour.get_by_role("button", name="Next")
    expect(close_button).to_be_focused()

    page.keyboard.press("Shift+Tab")
    expect(next_button).to_be_focused()
    page.keyboard.press("Tab")
    expect(close_button).to_be_focused()
    page.keyboard.press("Tab")
    expect(next_button).to_be_focused()

    page.keyboard.press("Escape")
    expect(tour).not_to_be_visible()
    expect(page.get_by_role("button", name="Help")).to_be_focused()


###############################################################################
def _prepare_training_guidance(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/training")
    page.wait_for_load_state("domcontentloaded")
    page.evaluate(f"localStorage.removeItem('{GUIDANCE_KEY}')")
    page.reload()
    page.wait_for_timeout(300)

###############################################################################
class TestGuidance:
    """The guidance layer should help once, then stay out of the way."""

    # -------------------------------------------------------------------------
    def test_training_walkthrough_is_manual_and_persisted(
        self, page: Page, base_url: str
    ):
        page.emulate_media(reduced_motion="reduce")
        _prepare_training_guidance(page, base_url)
        assert page.evaluate(
            "window.matchMedia('(prefers-reduced-motion: reduce)').matches"
        )

        expect(page.get_by_role("dialog")).not_to_be_visible()

        page.get_by_role("button", name="Help").click()
        tips = page.get_by_role("dialog", name="Tips & Tricks")
        expect(tips).to_be_visible()
        media_track = tips.locator(".guidance-media-track")
        expect(media_track).to_be_visible()
        assert media_track.evaluate(
            "element => getComputedStyle(element).animationName"
        ) == "none"
        launch_button = tips.get_by_role("button", name="Show the Training walkthrough")
        expect(
            tips.locator(".guidance-tour-heading").get_by_role("button")
        ).to_be_visible()
        expect(tips.get_by_role("button", name="Replay")).to_have_count(0)
        expect(tips.get_by_role("button", name="Reset guidance")).to_have_count(0)
        launch_button.click()

        tour = page.get_by_role("dialog", name="Start with data")
        expect(tour).to_be_visible()
        expect(tour.get_by_role("button", name="Close walkthrough")).to_be_focused()
        expect(page.get_by_text("Step 1 of 3", exact=True)).to_be_visible()
        expect(tour.get_by_role("button", name="Skip walkthrough")).to_have_count(0)

        page.get_by_role("button", name="Next").click()
        expect(page.get_by_role("dialog", name="Configure a run")).to_be_visible()
        page.get_by_role("button", name="Back").click()
        expect(page.get_by_role("dialog", name="Start with data")).to_be_visible()
        _assert_tour_keyboard_dismissal(page, "Start with data")
        page.wait_for_function(
            """() => {
                const state = JSON.parse(localStorage.getItem('fairs.guidance') || '{}');
                return state.entries?.['training-introduction']?.status === 'dismissed';
            }"""
        )

        page.reload()
        expect(page.get_by_role("dialog")).not_to_be_visible()

        help_button = page.get_by_role("button", name="Help")
        help_button.click()
        tips = page.get_by_role("dialog", name="Tips & Tricks")
        expect(tips).to_be_visible()
        expect(tips.get_by_text("Start with the generator", exact=True)).to_be_visible()

        page.keyboard.press("Escape")
        expect(tips).not_to_be_visible()
        expect(help_button).to_be_focused()

    # -------------------------------------------------------------------------
    def test_inference_walkthrough_is_manual_and_supports_back_navigation(
        self, page: Page, base_url: str
    ):
        page.emulate_media(reduced_motion="reduce")
        page.goto(f"{base_url}/inference")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(300)
        assert page.evaluate(
            "window.matchMedia('(prefers-reduced-motion: reduce)').matches"
        )

        expect(page.get_by_role("dialog")).not_to_be_visible()
        checkpoint_tip = page.get_by_role(
            "button", name="Dismiss Train a checkpoint first"
        )
        if checkpoint_tip.count() > 0:
            checkpoint_tip.click()
            page.reload()
            page.wait_for_timeout(300)
            expect(checkpoint_tip).not_to_be_visible()

        page.get_by_role("button", name="Help").click()
        tips = page.get_by_role("dialog", name="Tips & Tricks")
        expect(tips).to_be_visible()
        expect(tips).to_have_attribute("aria-modal", "true")
        expect(tips.get_by_role("button", name="Close Tips & Tricks")).to_be_focused()
        media_track = tips.locator(".guidance-media-track")
        expect(media_track).to_be_visible()
        assert media_track.evaluate(
            "element => getComputedStyle(element).animationName"
        ) == "none"

        tips.get_by_role("button", name="Show the Inference loop").click()
        tour = page.get_by_role("dialog", name="Set up a session")
        expect(tour).to_be_visible()
        expect(tour.get_by_role("button", name="Close walkthrough")).to_be_focused()
        expect(page.get_by_text("Step 1 of 3", exact=True)).to_be_visible()

        page.get_by_role("button", name="Next").click()
        expect(page.get_by_role("dialog", name="Get a prediction")).to_be_visible()
        expect(page.get_by_text("Step 2 of 3", exact=True)).to_be_visible()

        page.get_by_role("button", name="Back").click()
        expect(page.get_by_role("dialog", name="Set up a session")).to_be_visible()
        _assert_tour_keyboard_dismissal(page, "Set up a session")
        page.wait_for_function(
            """() => {
                const state = JSON.parse(localStorage.getItem('fairs.guidance') || '{}');
                return state.entries?.['inference-loop']?.status === 'dismissed';
            }"""
        )
        page.reload()
        expect(page.get_by_role("dialog")).not_to_be_visible()
