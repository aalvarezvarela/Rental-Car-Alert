# Rental Car Alert

`Rental Car Alert` monitors a saved `doyouspain.com` search with Playwright and sends an email when a qualifying offer drops below your configured price limit.

The project now targets `Python 3.12` and uses `Poetry` for environment and dependency management.

The supported entrypoints are:

```bash
python -m rental_car_alert
```

or, after an editable install:

```bash
rental-car-alert
```

Detailed documentation:

- [Setup Guide](/home/adrian_alvarez/Projects/Rental-Car-Alert/docs/SETUP.md)
- [Architecture Guide](/home/adrian_alvarez/Projects/Rental-Car-Alert/docs/ARCHITECTURE.md)

## Quick Start

```bash
poetry env use python3.12
poetry install
poetry run playwright install chromium
```

Run one cycle:

```bash
RCA_SMTP_PASSWORD="your-app-password" poetry run python -m rental_car_alert 115 --once
```

Run continuously:

```bash
poetry run python -m rental_car_alert 115
```

## What It Does

1. Opens your DoYouSpain results page in Playwright.
2. Accepts cookies and applies filters such as `Full/Full`.
3. Parses the result cards into structured `CarOffer` objects.
4. Opens each qualifying detail page to read the insurance-inclusive price.
5. Sends an email if a new result is below the configured threshold.
6. Waits for the next polling interval and repeats.

## Main Configuration

- `RCA_URL`: DoYouSpain results URL to monitor
- `RCA_PRICE_LIMIT`: Alert threshold in euros
- `RCA_EMAIL_TO`: Recipient email
- `RCA_EMAIL_FROM`: Sender email
- `RCA_SMTP_HOST`: SMTP host
- `RCA_SMTP_PORT`: SMTP port
- `RCA_SMTP_USERNAME`: SMTP username
- `RCA_SMTP_PASSWORD`: SMTP password or app password
- `RCA_HEADLESS`: `true` or `false`
- `RCA_INSURANCE_LIMIT`: Compare against insurance-inclusive price
- `RCA_ONLY_CANCELABLE`: Restrict to cancelable offers

The full setup and configuration reference is in [docs/SETUP.md](/home/adrian_alvarez/Projects/Rental-Car-Alert/docs/SETUP.md).
