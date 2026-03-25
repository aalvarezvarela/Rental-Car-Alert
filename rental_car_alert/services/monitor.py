from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta

from rental_car_alert.config import AppConfig
from rental_car_alert.notifications import build_email_body, serialize_alert_snapshot
from rental_car_alert.scrapers.doyouspain import DoyouSpainScraper
from rental_car_alert.services.email import EmailClient

LOGGER = logging.getLogger(__name__)


class RentalCarMonitor:
    def __init__(
        self,
        config: AppConfig,
        scraper: DoyouSpainScraper,
        email_client: EmailClient,
    ) -> None:
        self._config = config
        self._scraper = scraper
        self._email_client = email_client
        self._last_snapshot = ""

    def run_forever(self) -> None:
        while True:
            try:
                self.run_cycle()
            except Exception:
                LOGGER.exception("Monitoring cycle failed.")
                if self._config.monitor.run_once:
                    raise
                self._sleep(self._config.monitor.recovery_delay_seconds)
                continue

            if self._config.monitor.run_once:
                return

            self._sleep(self._build_wait_time())

    def run_cycle(self) -> None:
        LOGGER.info(
            "Starting lookup with limit %.2f € for %s (%s to %s)",
            self._config.search.limit,
            self._config.search.pickup_location,
            self._config.search.pickup_date.isoformat(),
            self._config.search.return_date.isoformat(),
        )
        search_run = self._scraper.fetch_offers(self._config.search)
        offers = search_run.offers
        alert_candidates = [
            offer
            for offer in offers
            if offer.qualifies_for_alert(
                limit=self._config.search.limit,
                insurance_limit=self._config.search.insurance_limit,
            )
        ]

        if not alert_candidates:
            LOGGER.info(
                "No cars found cheaper than %.2f €.",
                self._config.search.limit,
            )
            self._last_snapshot = ""
            return

        snapshot = serialize_alert_snapshot(
            alert_candidates,
            insurance_limit=self._config.search.insurance_limit,
        )
        if snapshot == self._last_snapshot:
            LOGGER.info("Results already notified in the previous lookup.")
            return

        subject = (
            f"Rental Car Alert: {len(alert_candidates)} offer(s) below "
            f"{self._config.search.limit:.2f} EUR"
        )
        text_body, html_body = build_email_body(
            offers=alert_candidates,
            insurance_limit=self._config.search.insurance_limit,
            limit=self._config.search.limit,
            url=search_run.results_url,
        )

        if self._email_client.send(subject, text_body, html_body):
            self._last_snapshot = snapshot
        else:
            LOGGER.warning("Alert email was not delivered.")

    def _build_wait_time(self) -> int:
        multiplier = random.uniform(
            self._config.monitor.jitter_min,
            self._config.monitor.jitter_max,
        )
        return max(1, int(self._config.monitor.poll_interval_seconds * multiplier))

    def _sleep(self, seconds: int) -> None:
        next_run = datetime.now() + timedelta(seconds=seconds)
        LOGGER.info(
            "Next search scheduled at %s (in %.2f hours).",
            next_run.strftime("%H:%M:%S"),
            seconds / 3600,
        )
        time.sleep(seconds)
