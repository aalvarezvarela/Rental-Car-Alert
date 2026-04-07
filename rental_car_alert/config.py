from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from rental_car_alert.models import (
    DEFAULT_ALLOWED_FUEL_POLICIES,
    normalize_fuel_policy,
)


DEFAULT_RECIPIENT = "adrianalvarez3091@gmail.com"
DEFAULT_SENDER = "rent.a.car.alert@gmail.com"
DEFAULT_PRICE_LIMIT = 115.0
DEFAULT_POLL_INTERVAL_SECONDS = 60 * 60
DEFAULT_RECOVERY_DELAY_SECONDS = 5 * 60
DEFAULT_JITTER_MIN = 0.7
DEFAULT_JITTER_MAX = 0.9
DEFAULT_TIMEOUT_MS = 15_000
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_BROWSER_LOCALE = "es-ES"
DEFAULT_BROWSER_TIMEZONE_ID = "Europe/Madrid"
DEFAULT_BROWSER_LATITUDE = 40.416775
DEFAULT_BROWSER_LONGITUDE = -3.703790
DEFAULT_BROWSER_GEOLOCATION_ACCURACY_METERS = 50
DEFAULT_ACCEPT_LANGUAGE = "es-ES,es;q=0.9,en;q=0.8"


def _load_dotenv() -> None:
    for base_path in [Path.cwd(), *Path.cwd().parents]:
        env_path = base_path / ".env"
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)
        return


def _parse_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_limit(raw_value: str) -> float:
    cleaned = raw_value.replace("€", "").replace(",", ".").strip()
    return float(cleaned)


def _parse_date(raw_value: str) -> date:
    normalized = raw_value.strip()
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Invalid date: {raw_value!r}. Use formats like 02-05-26 or 2026-05-02."
    )


def _parse_time(raw_value: str) -> time:
    normalized = raw_value.strip()
    for fmt in ("%H:%M", "%H %M", "%H%M"):
        try:
            return datetime.strptime(normalized, fmt).time()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Invalid time: {raw_value!r}. Use formats like 12:30 or 12 30."
    )


def _parse_fuel_policies(raw_value: str | None) -> frozenset[str]:
    if raw_value is None or not raw_value.strip():
        return DEFAULT_ALLOWED_FUEL_POLICIES

    normalized = raw_value.strip().lower()
    if normalized in {"any", "all", "*"}:
        return frozenset()

    policies = [
        normalize_fuel_policy(policy)
        for policy in raw_value.split(",")
        if policy.strip()
    ]
    if not policies:
        return DEFAULT_ALLOWED_FUEL_POLICIES
    return frozenset(policies)


@dataclass(frozen=True, slots=True)
class SearchSettings:
    pickup_location: str
    limit: float
    pickup_date: date
    return_date: date
    pickup_time: time | None
    insurance_limit: bool
    only_cancelable: bool
    fuel_policies: frozenset[str]


@dataclass(frozen=True, slots=True)
class BrowserSettings:
    headless: bool
    timeout_ms: int
    user_agent: str
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = DEFAULT_BROWSER_LOCALE
    timezone_id: str = DEFAULT_BROWSER_TIMEZONE_ID
    geolocation_latitude: float = DEFAULT_BROWSER_LATITUDE
    geolocation_longitude: float = DEFAULT_BROWSER_LONGITUDE
    geolocation_accuracy: int = DEFAULT_BROWSER_GEOLOCATION_ACCURACY_METERS
    accept_language: str = DEFAULT_ACCEPT_LANGUAGE
    proxy_server: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = None


@dataclass(frozen=True, slots=True)
class EmailSettings:
    recipient: str
    sender: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str


@dataclass(frozen=True, slots=True)
class MonitorSettings:
    poll_interval_seconds: int
    recovery_delay_seconds: int
    jitter_min: float
    jitter_max: float
    run_once: bool


@dataclass(frozen=True, slots=True)
class AppConfig:
    search: SearchSettings
    browser: BrowserSettings
    email: EmailSettings
    monitor: MonitorSettings


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor DoYouSpain offers and send email alerts."
    )
    parser.add_argument(
        "limit",
        nargs="?",
        type=_parse_limit,
        default=_parse_limit(os.getenv("RCA_PRICE_LIMIT", str(DEFAULT_PRICE_LIMIT))),
        help="Alert threshold in euros.",
    )
    parser.add_argument(
        "--pickup-location",
        default=os.getenv("RCA_PICKUP_LOCATION", ""),
        help="Pickup location text used in the DoYouSpain autocomplete.",
    )
    parser.add_argument(
        "--pickup-date",
        type=_parse_date,
        default=_parse_date(os.getenv("RCA_PICKUP_DATE"))
        if os.getenv("RCA_PICKUP_DATE")
        else None,
        help="Pickup date. Example: 02-05-26",
    )
    parser.add_argument(
        "--return-date",
        type=_parse_date,
        default=_parse_date(os.getenv("RCA_RETURN_DATE"))
        if os.getenv("RCA_RETURN_DATE")
        else None,
        help="Return date. Example: 09-05-26",
    )
    parser.add_argument(
        "--pickup-time",
        type=_parse_time,
        default=_parse_time(os.getenv("RCA_PICKUP_TIME"))
        if os.getenv("RCA_PICKUP_TIME")
        else None,
        help="Pickup time applied to both pickup and return. Example: 12:30",
    )
    parser.add_argument(
        "--recipient",
        default=os.getenv("RCA_EMAIL_TO", os.getenv("RCA_EMAIL", DEFAULT_RECIPIENT)),
        help="Email address that will receive alerts.",
    )
    parser.add_argument(
        "--sender",
        default=os.getenv("RCA_EMAIL_FROM", DEFAULT_SENDER),
        help="SMTP sender address.",
    )
    parser.add_argument(
        "--smtp-host",
        default=os.getenv("RCA_SMTP_HOST", "smtp.gmail.com"),
        help="SMTP hostname.",
    )
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=int(os.getenv("RCA_SMTP_PORT", "587")),
        help="SMTP port.",
    )
    parser.add_argument(
        "--smtp-username",
        default=os.getenv("RCA_SMTP_USERNAME", os.getenv("RCA_EMAIL_FROM", DEFAULT_SENDER)),
        help="SMTP username.",
    )
    parser.add_argument(
        "--smtp-password",
        default=os.getenv("RCA_SMTP_PASSWORD", ""),
        help="SMTP password or app password.",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=_parse_bool(os.getenv("RCA_HEADLESS"), False),
        help="Run the browser in headless mode.",
    )
    parser.add_argument(
        "--insurance-limit",
        action=argparse.BooleanOptionalAction,
        default=_parse_bool(os.getenv("RCA_INSURANCE_LIMIT"), True),
        help="Evaluate alerts using the total insurance-inclusive price.",
    )
    parser.add_argument(
        "--only-cancelable",
        action=argparse.BooleanOptionalAction,
        default=_parse_bool(os.getenv("RCA_ONLY_CANCELABLE"), False),
        help="Only inspect offers with free cancellation.",
    )
    parser.add_argument(
        "--fuel-policies",
        type=_parse_fuel_policies,
        default=_parse_fuel_policies(os.getenv("RCA_FUEL_POLICIES")),
        help=(
            "Comma-separated allowed fuel policies. Examples: "
            "'full/full,like for like' or 'any'."
        ),
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=int(os.getenv("RCA_INTERVAL_SECONDS", str(DEFAULT_POLL_INTERVAL_SECONDS))),
        help="Base polling interval.",
    )
    parser.add_argument(
        "--recovery-delay-seconds",
        type=int,
        default=int(
            os.getenv(
                "RCA_RECOVERY_DELAY_SECONDS",
                str(DEFAULT_RECOVERY_DELAY_SECONDS),
            )
        ),
        help="Delay after a failed cycle.",
    )
    parser.add_argument(
        "--jitter-min",
        type=float,
        default=float(os.getenv("RCA_JITTER_MIN", str(DEFAULT_JITTER_MIN))),
        help="Minimum multiplier applied to the interval.",
    )
    parser.add_argument(
        "--jitter-max",
        type=float,
        default=float(os.getenv("RCA_JITTER_MAX", str(DEFAULT_JITTER_MAX))),
        help="Maximum multiplier applied to the interval.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=int(os.getenv("RCA_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS))),
        help="Playwright timeout in milliseconds.",
    )
    parser.add_argument(
        "--browser-locale",
        default=os.getenv("RCA_BROWSER_LOCALE", DEFAULT_BROWSER_LOCALE),
        help="Browser locale used by Playwright.",
    )
    parser.add_argument(
        "--timezone-id",
        default=os.getenv("RCA_TIMEZONE_ID", DEFAULT_BROWSER_TIMEZONE_ID),
        help="Browser timezone used by Playwright.",
    )
    parser.add_argument(
        "--geolocation-latitude",
        type=float,
        default=float(os.getenv("RCA_GEOLOCATION_LATITUDE", str(DEFAULT_BROWSER_LATITUDE))),
        help="Latitude exposed to browser geolocation APIs.",
    )
    parser.add_argument(
        "--geolocation-longitude",
        type=float,
        default=float(os.getenv("RCA_GEOLOCATION_LONGITUDE", str(DEFAULT_BROWSER_LONGITUDE))),
        help="Longitude exposed to browser geolocation APIs.",
    )
    parser.add_argument(
        "--geolocation-accuracy",
        type=int,
        default=int(
            os.getenv(
                "RCA_GEOLOCATION_ACCURACY",
                str(DEFAULT_BROWSER_GEOLOCATION_ACCURACY_METERS),
            )
        ),
        help="Accuracy in meters exposed to browser geolocation APIs.",
    )
    parser.add_argument(
        "--accept-language",
        default=os.getenv("RCA_ACCEPT_LANGUAGE", DEFAULT_ACCEPT_LANGUAGE),
        help="Accept-Language header sent by Playwright.",
    )
    parser.add_argument(
        "--proxy-server",
        default=os.getenv("RCA_PROXY_SERVER"),
        help="Optional Playwright proxy server, for example http://host:port.",
    )
    parser.add_argument(
        "--proxy-username",
        default=os.getenv("RCA_PROXY_USERNAME"),
        help="Optional Playwright proxy username.",
    )
    parser.add_argument(
        "--proxy-password",
        default=os.getenv("RCA_PROXY_PASSWORD"),
        help="Optional Playwright proxy password.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=_parse_bool(os.getenv("RCA_RUN_ONCE"), False),
        help="Run a single polling cycle and exit.",
    )
    return parser


def load_config(argv: list[str] | None = None) -> AppConfig:
    _load_dotenv()
    args = build_argument_parser().parse_args(argv)

    if not args.pickup_location.strip():
        raise ValueError("pickup-location is required.")
    if args.pickup_date is None:
        raise ValueError("pickup-date is required.")
    if args.return_date is None:
        raise ValueError("return-date is required.")
    if args.return_date <= args.pickup_date:
        raise ValueError("return-date must be after pickup-date.")
    if args.jitter_min > args.jitter_max:
        raise ValueError("jitter-min cannot be greater than jitter-max.")
    if not args.browser_locale.strip():
        raise ValueError("browser-locale cannot be empty.")
    if not args.timezone_id.strip():
        raise ValueError("timezone-id cannot be empty.")
    if not args.accept_language.strip():
        raise ValueError("accept-language cannot be empty.")
    if not -90 <= args.geolocation_latitude <= 90:
        raise ValueError("geolocation-latitude must be between -90 and 90.")
    if not -180 <= args.geolocation_longitude <= 180:
        raise ValueError("geolocation-longitude must be between -180 and 180.")
    if args.geolocation_accuracy < 0:
        raise ValueError("geolocation-accuracy cannot be negative.")
    proxy_server = args.proxy_server.strip() if args.proxy_server else None
    proxy_username = args.proxy_username.strip() if args.proxy_username else None
    proxy_password = args.proxy_password.strip() if args.proxy_password else None
    if (proxy_username or proxy_password) and not proxy_server:
        raise ValueError("proxy-username and proxy-password require proxy-server.")

    return AppConfig(
        search=SearchSettings(
            pickup_location=args.pickup_location.strip(),
            limit=args.limit,
            pickup_date=args.pickup_date,
            return_date=args.return_date,
            pickup_time=args.pickup_time,
            insurance_limit=args.insurance_limit,
            only_cancelable=args.only_cancelable,
            fuel_policies=args.fuel_policies,
        ),
        browser=BrowserSettings(
            headless=args.headless,
            timeout_ms=args.timeout_ms,
            user_agent=DEFAULT_USER_AGENT,
            locale=args.browser_locale.strip(),
            timezone_id=args.timezone_id.strip(),
            geolocation_latitude=args.geolocation_latitude,
            geolocation_longitude=args.geolocation_longitude,
            geolocation_accuracy=args.geolocation_accuracy,
            accept_language=args.accept_language.strip(),
            proxy_server=proxy_server,
            proxy_username=proxy_username,
            proxy_password=proxy_password,
        ),
        email=EmailSettings(
            recipient=args.recipient,
            sender=args.sender,
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            smtp_username=args.smtp_username,
            smtp_password=args.smtp_password,
        ),
        monitor=MonitorSettings(
            poll_interval_seconds=args.interval_seconds,
            recovery_delay_seconds=args.recovery_delay_seconds,
            jitter_min=args.jitter_min,
            jitter_max=args.jitter_max,
            run_once=args.once,
        ),
    )
