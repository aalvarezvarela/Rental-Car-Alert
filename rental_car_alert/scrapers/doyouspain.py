from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from rental_car_alert.config import BrowserSettings, SearchSettings
from rental_car_alert.models import CarOffer
from rental_car_alert.parsers.doyouspain import get_insurance_price, parse_offers

LOGGER = logging.getLogger(__name__)


class DoyouSpainScraper:
    def __init__(self, browser_settings: BrowserSettings) -> None:
        self._browser_settings = browser_settings

    def fetch_offers(self, search_settings: SearchSettings) -> list[CarOffer]:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is required. Install dependencies and run "
                "`playwright install chromium` before starting the monitor."
            ) from exc

        offers: list[CarOffer] = []
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
                self._open_results(page, search_settings.url)
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
            finally:
                context.close()
                browser.close()

        return offers

    def _open_results(self, page, url: str) -> None:
        LOGGER.info("Opening search page.")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1_000)

    def _apply_filters(self, page, only_cancelable: bool, timeout_error: type[Exception]) -> None:
        self._click_optional(page, "#checkAllOptions", "cookie acceptance", timeout_error)
        self._click_optional(
            page,
            "#idSearchButton button#sendForm",
            "search button",
            timeout_error,
        )
        page.wait_for_timeout(5_000)

        fuel_selectors = (
            '.fuel-option.fuel-option-none.tooltipBlancoBig[title*="Full/Full"]',
            '.fuel-option.fuel-option-none.tooltipBlancoBig[title*="Lleno/Lleno"]',
        )
        for selector in fuel_selectors:
            if self._click_optional(page, selector, f"fuel filter {selector}", timeout_error):
                page.wait_for_timeout(2_000)
                break

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
        return offers

    def _populate_insurance_prices(
        self,
        page,
        search_settings: SearchSettings,
        offers: list[CarOffer],
        timeout_error: type[Exception],
    ) -> None:
        for offer in offers:
            LOGGER.info(
                "Checking base price for %s: %.2f €",
                offer.model,
                offer.price_without_insurance,
            )
            if not offer.price_without_insurance < search_settings.limit:
                continue
            if not offer.is_fuel_policy_allowed():
                continue
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
