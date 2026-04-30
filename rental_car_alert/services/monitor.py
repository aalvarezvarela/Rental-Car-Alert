from __future__ import annotations

import logging
import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from rental_car_alert.config import AppConfig
from rental_car_alert.models import CarOffer
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
        self._last_snapshot = self._load_last_snapshot()

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
        today = self._today()
        if today >= self._config.search.pickup_date:
            LOGGER.info(
                "Skipping lookup because today is %s and the rental starts on %s.",
                today.isoformat(),
                self._config.search.pickup_date.isoformat(),
            )
            self._set_last_snapshot("")
            return

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
                allowed_fuel_policies=self._config.search.fuel_policies,
            )
        ]

        if not alert_candidates:
            LOGGER.info(
                "No cars found cheaper than %.2f €.",
                self._config.search.limit,
            )
            self._log_rejected_offers(offers)
            self._set_last_snapshot("")
            return

        snapshot = serialize_alert_snapshot(
            alert_candidates,
            insurance_limit=self._config.search.insurance_limit,
        )
        if snapshot == self._last_snapshot:
            LOGGER.info("Results already notified in the previous lookup.")
            return

        subject = self._build_email_subject(len(alert_candidates))
        text_body, html_body = build_email_body(
            offers=alert_candidates,
            insurance_limit=self._config.search.insurance_limit,
            limit=self._config.search.limit,
            url=search_run.results_url,
        )

        if self._email_client.send(subject, text_body, html_body):
            self._set_last_snapshot(snapshot)
        else:
            LOGGER.warning("Alert email was not delivered.")

    def _build_email_subject(self, alert_count: int) -> str:
        offer_label = "offer" if alert_count == 1 else "offers"
        price_mode = (
            "with insurance"
            if self._config.search.insurance_limit
            else "base price"
        )
        return (
            f"{self._config.search.pickup_location}: "
            f"{alert_count} {offer_label} under "
            f"{self._config.search.limit:.2f} EUR "
            f"({price_mode}, "
            f"{self._config.search.pickup_date.isoformat()} to "
            f"{self._config.search.return_date.isoformat()})"
        )

    def _log_rejected_offers(self, offers: list[CarOffer]) -> None:
        for offer in offers:
            alert_price = offer.alert_price(self._config.search.insurance_limit)
            price_label = "unknown" if alert_price is None else f"{alert_price:.2f} EUR"
            reasons = []
            if alert_price is None:
                reasons.append("missing comparison price")
            elif alert_price >= self._config.search.limit:
                reasons.append("price is not below limit")
            if not offer.is_fuel_policy_allowed(self._config.search.fuel_policies):
                reasons.append(f"fuel policy {offer.fuel_policy!r} is not allowed")
            LOGGER.info(
                "Rejected offer #%s %s: %s (%s).",
                offer.position + 1,
                offer.model,
                price_label,
                ", ".join(reasons) or "unknown reason",
            )

    def _load_last_snapshot(self) -> str:
        snapshot_file = self._config.monitor.snapshot_file
        if snapshot_file is None:
            return ""

        try:
            snapshot = snapshot_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""
        except OSError:
            LOGGER.exception("Failed to read alert snapshot from %s.", snapshot_file)
            return ""

        LOGGER.info("Loaded previous alert snapshot from %s.", snapshot_file)
        return snapshot

    def _set_last_snapshot(self, snapshot: str) -> None:
        self._last_snapshot = snapshot
        self._save_last_snapshot(snapshot)

    def _save_last_snapshot(self, snapshot: str) -> None:
        snapshot_file = self._config.monitor.snapshot_file
        if snapshot_file is None:
            return

        try:
            snapshot_file.parent.mkdir(parents=True, exist_ok=True)
            temporary_file = self._temporary_snapshot_file(snapshot_file)
            temporary_file.write_text(snapshot, encoding="utf-8")
            temporary_file.replace(snapshot_file)
        except OSError:
            LOGGER.exception("Failed to write alert snapshot to %s.", snapshot_file)

    def _temporary_snapshot_file(self, snapshot_file: Path) -> Path:
        return snapshot_file.with_name(f"{snapshot_file.name}.tmp")

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

    def _today(self) -> date:
        return datetime.now().astimezone().date()
