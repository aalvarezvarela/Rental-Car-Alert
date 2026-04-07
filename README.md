# Rental Car Alert

`Rental Car Alert` opens `doyouspain.com`, fills the search form with your pickup location and dates, then sends an email when a qualifying offer drops below your configured price limit.

The project now targets `Python 3.12` and uses `Poetry` for environment and dependency management.

Configuration can be supplied either with CLI flags or a local `.env` file in the project root.

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
RCA_PICKUP_LOCATION="heraclion" \
RCA_PICKUP_DATE="02-05-26" \
RCA_RETURN_DATE="09-05-26" \
RCA_PICKUP_TIME="12 30" \
RCA_SMTP_PASSWORD="your-app-password" \
poetry run python -m rental_car_alert 115 --once
```

With the included `.env`, you can also just run:

```bash
poetry run python -m rental_car_alert 115 --once
```

Run continuously:

```bash
RCA_PICKUP_LOCATION="heraclion" \
RCA_PICKUP_DATE="02-05-26" \
RCA_RETURN_DATE="09-05-26" \
RCA_PICKUP_TIME="12 30" \
poetry run python -m rental_car_alert 115
```

## What It Does

1. Opens the DoYouSpain homepage in Playwright.
2. Fills the pickup autocomplete with your location text and selects the first matching option.
3. Sets pickup and return dates, then submits the search.
4. Applies filters such as `Full/Full`.
5. Parses the result cards into structured `CarOffer` objects.
6. Opens each qualifying detail page to read the insurance-inclusive price.
7. Sends an email if a new result is below the configured threshold.
8. Waits for the next polling interval and repeats.

## Main Configuration

- `RCA_PICKUP_LOCATION`: Pickup location text, for example `heraclion`
- `RCA_PICKUP_DATE`: Pickup date, for example `02-05-26`
- `RCA_RETURN_DATE`: Return date, for example `09-05-26`
- `RCA_PICKUP_TIME`: Optional pickup time applied to both pickup and return, for example `12 30`
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
- `RCA_BROWSER_LOCALE`: Browser locale, defaults to `es-ES`
- `RCA_TIMEZONE_ID`: Browser timezone, defaults to `Europe/Madrid`
- `RCA_PROXY_SERVER`: Optional proxy URL if the site needs to see a Spanish IP

The full setup and configuration reference is in [docs/SETUP.md](/home/adrian_alvarez/Projects/Rental-Car-Alert/docs/SETUP.md).

## GitHub Actions

The repository includes [rental-car-alert.yml](/home/adrian_alvarez/Projects/Rental-Car-Alert/.github/workflows/rental-car-alert.yml), which runs headlessly on GitHub Actions every 6 hours and can also be started manually.

It is preconfigured for:

- pickup location: `Heraclion Airport`
- pickup date: `2026-06-21`
- return date: `2026-07-08`
- pickup/return time: `12 30`

To make it work, add these repository secrets:

- `RCA_EMAIL_TO`
- `RCA_EMAIL_FROM`
- `RCA_SMTP_HOST`
- `RCA_SMTP_PORT`
- `RCA_SMTP_USERNAME`
- `RCA_SMTP_PASSWORD`
