from __future__ import annotations

import logging
import random
from datetime import date, datetime, time
from pathlib import Path

from bs4 import BeautifulSoup

from rental_car_alert.config import BrowserSettings, SearchSettings
from rental_car_alert.models import CarOffer, SearchRun
from rental_car_alert.parsers.doyouspain import get_insurance_price, parse_offers

LOGGER = logging.getLogger(__name__)
HOME_URL = "https://www.doyouspain.com/alquiler-coches/"
DEBUG_DIR = Path("debug_artifacts")
LOG_PREVIEW_LIMIT = 4_000
MIN_HUMAN_PAUSE_SECONDS = 0.6
MAX_HUMAN_PAUSE_SECONDS = 2.0


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
            launch_options = {
                "headless": self._browser_settings.headless,
                "args": ["--disable-dev-shm-usage", "--no-sandbox"],
            }
            proxy_settings = self._playwright_proxy_settings()
            if proxy_settings is not None:
                launch_options["proxy"] = proxy_settings

            browser = playwright.chromium.launch(**launch_options)
            context = browser.new_context(
                user_agent=self._browser_settings.user_agent,
                viewport={
                    "width": self._browser_settings.viewport_width,
                    "height": self._browser_settings.viewport_height,
                },
                locale=self._browser_settings.locale,
                timezone_id=self._browser_settings.timezone_id,
                geolocation={
                    "latitude": self._browser_settings.geolocation_latitude,
                    "longitude": self._browser_settings.geolocation_longitude,
                    "accuracy": self._browser_settings.geolocation_accuracy,
                },
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept-Language": self._browser_settings.accept_language,
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

    def _playwright_proxy_settings(self) -> dict[str, str] | None:
        if self._browser_settings.proxy_server is None:
            return None

        proxy_settings = {"server": self._browser_settings.proxy_server}
        if self._browser_settings.proxy_username is not None:
            proxy_settings["username"] = self._browser_settings.proxy_username
        if self._browser_settings.proxy_password is not None:
            proxy_settings["password"] = self._browser_settings.proxy_password
        return proxy_settings

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
        page.wait_for_timeout(1_500)
        self._select_first_pickup_suggestion(page, timeout_error)

        self._set_date_input(page, "#fechaRecogida", search_settings.pickup_date)
        self._set_date_input(page, "#fechaDevolucion", search_settings.return_date)
        if search_settings.pickup_time is not None:
            self._set_time_input(
                page,
                hour_selector="#horarecogida",
                minute_selector="#minutosrecogida",
                value=search_settings.pickup_time,
            )
            self._set_time_input(
                page,
                hour_selector="#horadevolucion",
                minute_selector="#minutosdevolucion",
                value=search_settings.pickup_time,
            )
        self._log_form_state(page)
        LOGGER.info(
            "Searching for offers from %s to %s%s.",
            search_settings.pickup_date.isoformat(),
            search_settings.return_date.isoformat(),
            (
                f" at {search_settings.pickup_time.strftime('%H:%M')}"
                if search_settings.pickup_time is not None
                else ""
            ),
        )

        self._human_pause(page)
        page.locator("#sendForm").click(no_wait_after=True)
        try:
            page.wait_for_url("**/do/list/**", timeout=5_000)
        except timeout_error:
            self._wait_for_results(page, timeout_error)
        page.wait_for_timeout(3_000)

    def _set_date_input(self, page, selector: str, value: date) -> None:
        formatted = value.strftime("%d/%m/%Y")
        page.evaluate(
            """
            ({ selector, formatted, isoDate }) => {
                const element = document.querySelector(selector);
                if (!element) {
                    return false;
                }

                const jq = window.jQuery || window.$;
                const parsedDate = new Date(`${isoDate}T12:00:00`);

                if (jq && jq.fn && typeof jq.fn.datepicker === 'function') {
                    jq(element).datepicker('setDate', parsedDate);
                }

                element.removeAttribute('readonly');
                element.value = formatted;
                element.setAttribute('value', formatted);
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                element.dispatchEvent(new Event('blur', { bubbles: true }));
                return true;
            }
            """,
            {
                "selector": selector,
                "formatted": formatted,
                "isoDate": value.isoformat(),
            },
        )
        page.wait_for_function(
            """({ selector, formatted }) => {
                const element = document.querySelector(selector);
                return !!element && element.value === formatted;
            }""",
            arg={"selector": selector, "formatted": formatted},
        )

    def _set_time_input(
        self,
        page,
        hour_selector: str,
        minute_selector: str,
        value: time,
    ) -> None:
        page.evaluate(
            """
            ({ hourSelector, minuteSelector, hour, minute }) => {
                const setSelect = (selector, rawValue) => {
                    const element = document.querySelector(selector);
                    if (!element) {
                        return false;
                    }

                    const candidates = [
                        rawValue,
                        rawValue.padStart(2, '0'),
                        String(Number(rawValue)),
                    ];
                    const options = Array.from(element.options || []);
                    const matchedOption = options.find((option) => {
                        const optionValue = (option.value || '').trim();
                        const optionText = (option.textContent || '').trim();
                        return candidates.includes(optionValue) || candidates.includes(optionText);
                    });

                    const nextValue = matchedOption ? matchedOption.value : rawValue;
                    element.value = nextValue;
                    element.setAttribute('value', nextValue);
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('blur', { bubbles: true }));
                    return element.value === nextValue;
                };

                return (
                    setSelect(hourSelector, hour) &&
                    setSelect(minuteSelector, minute)
                );
            }
            """,
            {
                "hourSelector": hour_selector,
                "minuteSelector": minute_selector,
                "hour": value.strftime("%H"),
                "minute": value.strftime("%M"),
            },
        )
        page.wait_for_function(
            """
            ({ hourSelector, minuteSelector, hour, minute }) => {
                const matches = (selector, expected) => {
                    const element = document.querySelector(selector);
                    if (!element) {
                        return false;
                    }
                    const normalized = [expected, String(Number(expected))];
                    return normalized.includes(element.value);
                };

                return matches(hourSelector, hour) && matches(minuteSelector, minute);
            }
            """,
            arg={
                "hourSelector": hour_selector,
                "minuteSelector": minute_selector,
                "hour": value.strftime("%H"),
                "minute": value.strftime("%M"),
            },
        )

    def _select_first_pickup_suggestion(self, page, timeout_error: type[Exception]) -> None:
        suggestion = page.locator("#recogida_lista li").first
        suggestion.wait_for(state="visible")
        option_data = suggestion.evaluate(
            """
            (element) => ({
                id: element.dataset.id || '',
                destino: element.dataset.destino || '',
                pais: element.dataset.pais || '',
                destinoDescription: element.dataset.destinoDescription || '',
                label: (element.textContent || '').replace(/\\s+/g, ' ').trim(),
            })
            """
        )

        try:
            self._human_pause(page)
            suggestion.click(timeout=self._browser_settings.timeout_ms, force=True)
            page.wait_for_timeout(300)
        except timeout_error:
            LOGGER.warning("Suggestion click timed out; applying destination fields directly.")

        page.evaluate(
            """
            (option) => {
                const applyValue = (selector, value) => {
                    const element = document.querySelector(selector);
                    if (!element) {
                        return;
                    }
                    element.value = value;
                    element.setAttribute('value', value);
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('blur', { bubbles: true }));
                };

                applyValue('#pickup', option.id || option.destinoDescription || option.label || '');
                applyValue('#destino', option.destino || '');
                applyValue('#destino_final', option.destino || '');
                applyValue('#pais', option.pais || '');
                applyValue('#codDestinoLanding', option.destino || '');
                applyValue('#paisLanding', option.pais || '');
            }
            """,
            option_data,
        )

        state = self._read_form_state(page)
        for _ in range(20):
            if state["destino"] and state["pickup"]:
                break
            page.wait_for_timeout(200)
            state = self._read_form_state(page)
        else:
            raise RuntimeError(
                "Pickup autocomplete did not populate the submitted destination fields."
            )
        LOGGER.info(
            "Selected first pickup suggestion: %s (%s).",
            option_data["id"] or option_data["label"],
            option_data["destino"],
        )

    def _log_form_state(self, page) -> None:
        state = self._read_form_state(page)
        LOGGER.info("Search form state before submit: %s", state)

    def _read_form_state(self, page) -> dict[str, str]:
        return page.evaluate(
            """
            () => ({
                pickup: document.querySelector('#pickup')?.value || '',
                destino: document.querySelector('#destino')?.value || '',
                destinoFinal: document.querySelector('#destino_final')?.value || '',
                pais: document.querySelector('#pais')?.value || '',
                pickupDate: document.querySelector('#fechaRecogida')?.value || '',
                returnDate: document.querySelector('#fechaDevolucion')?.value || '',
                pickupHour: document.querySelector('#horarecogida')?.value || '',
                pickupMinutes: document.querySelector('#minutosrecogida')?.value || '',
                returnHour: document.querySelector('#horadevolucion')?.value || '',
                returnMinutes: document.querySelector('#minutosdevolucion')?.value || '',
            })
            """
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
            self._human_pause(page)
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
            if not offer.is_fuel_policy_allowed(search_settings.fuel_policies):
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
                self._human_pause(page)
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

    def _human_pause(self, page) -> None:
        pause_seconds = random.uniform(
            MIN_HUMAN_PAUSE_SECONDS,
            MAX_HUMAN_PAUSE_SECONDS,
        )
        page.wait_for_timeout(int(pause_seconds * 1000))
