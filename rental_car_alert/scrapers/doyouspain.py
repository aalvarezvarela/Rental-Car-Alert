from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from rental_car_alert.config import BrowserSettings, SearchSettings
from rental_car_alert.models import CarOffer, SearchRun
from rental_car_alert.parsers.doyouspain import get_insurance_price, parse_offers

LOGGER = logging.getLogger(__name__)
HOME_URL = "https://www.doyouspain.com/alquiler-coches/"
DEBUG_DIR = Path("debug_artifacts")
LOG_PREVIEW_LIMIT = 4_000


class DoyouSpainScraper:
    def __init__(self, browser_settings: BrowserSettings) -> None:
        self._browser_settings = browser_settings

    def fetch_offers(self, search_settings: SearchSettings) -> SearchRun:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is required. Install dependencies and run "
                "`playwright install chromium` before starting the monitor."
            ) from exc

        offers: list[CarOffer] = []
        results_url = ""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=self._browser_settings.headless,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            context = browser.new_context(
                user_agent=self._browser_settings.user_agent,
                viewport={
                    "width": self._browser_settings.viewport_width,
                    "height": self._browser_settings.viewport_height,
                },
                ignore_https_errors=True,
            )
            page = context.new_page()
            page.set_default_timeout(self._browser_settings.timeout_ms)

            try:
                self._open_homepage(page)
                self._perform_search(
                    page=page,
                    search_settings=search_settings,
                    timeout_error=PlaywrightTimeoutError,
                )
                self._apply_filters(
                    page=page,
                    only_cancelable=search_settings.only_cancelable,
                    timeout_error=PlaywrightTimeoutError,
                )
                offers = self._parse_results(page)
                self._populate_insurance_prices(
                    page=page,
                    search_settings=search_settings,
                    offers=offers,
                    timeout_error=PlaywrightTimeoutError,
                )
                results_url = page.url
            finally:
                context.close()
                browser.close()

        return SearchRun(offers=offers, results_url=results_url)

    def _open_homepage(self, page) -> None:
        LOGGER.info("Opening DoYouSpain homepage.")
        page.goto(HOME_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(1_000)

    def _perform_search(
        self,
        page,
        search_settings: SearchSettings,
        timeout_error: type[Exception],
    ) -> None:
        self._click_optional(page, "#checkAllOptions", "cookie acceptance", timeout_error)

        pickup_input = page.locator("#pickup")
        pickup_input.wait_for(state="visible")
        LOGGER.info("Filling pickup location with %r.", search_settings.pickup_location)
        pickup_input.fill(search_settings.pickup_location)

        suggestion = page.locator("#recogida_lista li").first
        suggestion.wait_for(state="visible")
        suggestion.click()
        page.wait_for_timeout(500)
        LOGGER.info("Selected first pickup suggestion.")

        self._set_date_input(page, "#fechaRecogida", search_settings.pickup_date)
        self._set_date_input(page, "#fechaDevolucion", search_settings.return_date)
        LOGGER.info(
            "Searching for offers from %s to %s.",
            search_settings.pickup_date.isoformat(),
            search_settings.return_date.isoformat(),
        )

        page.locator("#sendForm").click(no_wait_after=True)
        try:
            page.wait_for_url("**/do/list/**", timeout=5_000)
        except timeout_error:
            self._wait_for_results(page, timeout_error)
        page.wait_for_timeout(3_000)

    def _set_date_input(self, page, selector: str, value: date) -> None:
        formatted = value.strftime("%d/%m/%Y")
        page.locator(selector).evaluate(
            """
            (element, nextValue) => {
                element.removeAttribute('readonly');
                element.value = nextValue;
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                element.dispatchEvent(new Event('blur', { bubbles: true }));
            }
            """,
            formatted,
        )

    def _apply_filters(self, page, only_cancelable: bool, timeout_error: type[Exception]) -> None:
        self._wait_for_results(page, timeout_error)

        if only_cancelable:
            if self._click_optional(page, "#idCancel1", "cancelation filter", timeout_error):
                page.wait_for_timeout(2_000)

        self._wait_for_results(page, timeout_error)

    def _wait_for_results(self, page, timeout_error: type[Exception]) -> None:
        try:
            page.locator("section.newcarlist.price-per-day article").first.wait_for()
        except timeout_error:
            LOGGER.warning("No offer cards became visible before the timeout expired.")

    def _click_optional(
        self,
        page,
        selector: str,
        description: str,
        timeout_error: type[Exception],
    ) -> bool:
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible")
            locator.click()
            LOGGER.info("Clicked %s.", description)
            return True
        except timeout_error:
            LOGGER.debug("Skipping %s; selector not available: %s", description, selector)
            return False

    def _parse_results(self, page) -> list[CarOffer]:
        page_content = page.content()
        soup = BeautifulSoup(page_content, features="lxml")
        offers = parse_offers(soup)
        LOGGER.info("Parsed %s offers from the results page.", len(offers))
        if not offers:
            self._dump_page_diagnostics(page, "empty_results")
        return offers

    def _dump_page_diagnostics(self, page, reason: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{reason}_{timestamp}"
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)

        html_path = DEBUG_DIR / f"{base_name}.html"
        screenshot_path = DEBUG_DIR / f"{base_name}.png"
        html_content = ""

        try:
            html_content = page.content()
            html_path.write_text(html_content, encoding="utf-8")
        except Exception:
            LOGGER.exception("Failed to write page HTML diagnostics.")
            html_path = None

        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception:
            LOGGER.exception("Failed to write page screenshot diagnostics.")
            screenshot_path = None

        try:
            body_preview = page.evaluate(
                "() => (document.body?.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 2000)"
            )
        except Exception:
            body_preview = ""

        LOGGER.warning("Empty results diagnostics URL: %s", page.url)
        LOGGER.warning("Empty results diagnostics title: %s", page.title())
        if body_preview:
            LOGGER.warning("Empty results diagnostics body preview: %s", body_preview)
        if html_content:
            LOGGER.warning(
                "Empty results diagnostics HTML preview (%s chars): %s",
                min(len(html_content), LOG_PREVIEW_LIMIT),
                html_content[:LOG_PREVIEW_LIMIT],
            )
        if html_path is not None:
            LOGGER.warning("Saved page HTML diagnostics to %s", html_path)
        if screenshot_path is not None:
            LOGGER.warning("Saved page screenshot diagnostics to %s", screenshot_path)

    def _populate_insurance_prices(
        self,
        page,
        search_settings: SearchSettings,
        offers: list[CarOffer],
        timeout_error: type[Exception],
    ) -> None:
        for offer in offers:
            LOGGER.debug(
                "Offer %s base price: %.2f €",
                offer.model,
                offer.price_without_insurance,
            )
            if not offer.price_without_insurance < search_settings.limit:
                continue
            if not offer.is_fuel_policy_allowed():
                continue
            LOGGER.info(
                "Opening detail popup for %s at %.2f €.",
                offer.model,
                offer.price_without_insurance,
            )
            detail_button = page.locator(f'[name="coche{offer.position + 1}"]').first

            if detail_button.count() == 0:
                LOGGER.warning(
                    "Missing detail button for offer #%s (%s).",
                    offer.position + 1,
                    offer.model,
                )
                continue

            popup = None
            try:
                detail_button.scroll_into_view_if_needed()
                with page.expect_popup(timeout=self._browser_settings.timeout_ms) as popup_info:
                    detail_button.click(
                        timeout=self._browser_settings.timeout_ms,
                        no_wait_after=True,
                    )
                popup = popup_info.value
                popup.wait_for_load_state("domcontentloaded")
                popup.wait_for_timeout(1_500)
                detail_soup = BeautifulSoup(popup.content(), features="lxml")
                insurance_price = get_insurance_price(
                    newsoup=detail_soup,
                    original_price=offer.price_without_insurance,
                )
            except timeout_error:
                LOGGER.warning(
                    "Unable to open the detail page for offer #%s.",
                    offer.position + 1,
                )
                continue
            finally:
                if popup is not None:
                    popup.close()

            if isinstance(insurance_price, float):
                offer.insurance_price = insurance_price
                LOGGER.info(
                    "Price including insurance for %s: %.2f €",
                    offer.model,
                    insurance_price,
                )
            else:
                LOGGER.warning(
                    "Insurance price could not be determined for %s.",
                    offer.model,
                )
