from __future__ import annotations

import logging

from rental_car_alert.config import load_config
from rental_car_alert.scrapers.doyouspain import DoyouSpainScraper
from rental_car_alert.services.email import EmailClient
from rental_car_alert.services.monitor import RentalCarMonitor


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    config = load_config(argv)
    monitor = RentalCarMonitor(
        config=config,
        scraper=DoyouSpainScraper(config.browser),
        email_client=EmailClient(config.email),
    )
    monitor.run_forever()
    return 0
