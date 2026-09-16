"""Browser coverage for the runtime Settings screen."""

from playwright.sync_api import Page, expect


###############################################################################
class TestSettingsPage:
    """The Settings screen should persist only its supported runtime fields."""

    # -------------------------------------------------------------------------
    def test_settings_edit_reload_reset_and_navigation(
        self, page: Page, base_url: str
    ):
        page.goto(f"{base_url}/settings")
        page.wait_for_load_state("networkidle")

        expect(page.get_by_role("heading", name="Settings", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Training polling", exact=True)).to_be_visible()
        expect(
            page.get_by_role("heading", name="JIT model construction", exact=True)
        ).to_be_visible()
        expect(page.get_by_role("link", name="Settings", exact=True)).to_have_attribute(
            "aria-current", "page"
        )

        polling = page.get_by_label("Training polling interval", exact=True)
        jit_compile = page.get_by_label("Enable JIT compilation", exact=True)
        jit_backend = page.get_by_label("JIT backend", exact=True)

        expect(polling).to_be_visible()
        expect(jit_compile).to_be_visible()
        expect(jit_backend).to_be_disabled()

        polling.fill("2.5")
        page.get_by_role("button", name="Save settings", exact=True).click()
        expect(page.get_by_text("Settings saved.", exact=True)).to_be_visible()

        page.reload()
        page.wait_for_load_state("networkidle")
        expect(polling).to_have_value("2.5")

        jit_compile.check()
        expect(jit_backend).to_be_enabled()
        jit_backend.fill("eager")
        page.get_by_role("button", name="Save settings", exact=True).click()
        expect(page.get_by_text("Settings saved.", exact=True)).to_be_visible()

        page.reload()
        page.wait_for_load_state("networkidle")
        expect(jit_compile).to_be_checked()
        expect(jit_backend).to_have_value("eager")

        page.get_by_role("button", name="Reset to defaults", exact=True).click()
        expect(page.get_by_text("Settings reset to defaults.", exact=True)).to_be_visible()
        expect(polling).to_have_value("1")
        expect(jit_compile).not_to_be_checked()
        expect(jit_backend).to_have_value("inductor")
        expect(jit_backend).to_be_disabled()

        page.get_by_role("button", name="Help", exact=True).click()
        expect(page.get_by_role("dialog", name="Tips & Tricks")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog", name="Tips & Tricks")).not_to_be_visible()

        page.get_by_role("link", name="Training", exact=True).click()
        expect(page).to_have_url(f"{base_url}/training")
        page.get_by_role("link", name="Settings", exact=True).click()
        expect(page).to_have_url(f"{base_url}/settings")

        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
