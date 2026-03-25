from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


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


@dataclass(frozen=True, slots=True)
class SearchSettings:
    pickup_location: str
    limit: float
    pickup_date: date
    return_date: date
    insurance_limit: bool
    only_cancelable: bool


@dataclass(frozen=True, slots=True)
class BrowserSettings:
    headless: bool
    timeout_ms: int
    user_agent: str
    viewport_width: int = 1920
    viewport_height: int = 1080


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

    return AppConfig(
        search=SearchSettings(
            pickup_location=args.pickup_location.strip(),
            limit=args.limit,
            pickup_date=args.pickup_date,
            return_date=args.return_date,
            insurance_limit=args.insurance_limit,
            only_cancelable=args.only_cancelable,
        ),
        browser=BrowserSettings(
            headless=args.headless,
            timeout_ms=args.timeout_ms,
            user_agent=DEFAULT_USER_AGENT,
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
