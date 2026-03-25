# Setup Guide

## Requirements

- Python `3.12`
- Poetry
- Playwright Chromium browser binaries
- An SMTP account that can send mail

## Installation

From the project root:

```bash
poetry env use python3.12
poetry install
poetry run playwright install chromium
```

This project includes a local [poetry.toml](/home/adrian_alvarez/Projects/Rental-Car-Alert/poetry.toml), so Poetry creates the environment inside the repository at `.venv/`.

## How To Run It

Single cycle:

```bash
poetry run python -m rental_car_alert 115 --once
```

Long-running monitor:

```bash
poetry run python -m rental_car_alert 115
```

Installed console script:

```bash
poetry run rental-car-alert 115 --once
```

The positional `115` is the price limit in euros. If omitted, the application uses `RCA_PRICE_LIMIT`, then falls back to `115`.

## Required Runtime Configuration

At minimum, configure:

- `RCA_URL`
- `RCA_EMAIL_TO`
- `RCA_SMTP_HOST`
- `RCA_SMTP_PORT`
- `RCA_SMTP_USERNAME`
- `RCA_SMTP_PASSWORD`

Example:

```bash
export RCA_URL='https://www.doyouspain.com/do/list/en?s=...&b=...'
export RCA_EMAIL_TO='you@example.com'
export RCA_EMAIL_FROM='alerts@example.com'
export RCA_SMTP_HOST='smtp.gmail.com'
export RCA_SMTP_PORT='587'
export RCA_SMTP_USERNAME='alerts@example.com'
export RCA_SMTP_PASSWORD='your-app-password'
```

Then run:

```bash
poetry run python -m rental_car_alert 115 --once
```

## Full CLI Reference

```bash
poetry run python -m rental_car_alert [limit] [options]
```

Options:

- `--url`: Override the monitored DoYouSpain URL
- `--recipient`: Override the destination email
- `--sender`: Override the sender email
- `--smtp-host`: SMTP server hostname
- `--smtp-port`: SMTP server port
- `--smtp-username`: SMTP username
- `--smtp-password`: SMTP password
- `--headless` or `--no-headless`: Run browser headless or visible
- `--insurance-limit` or `--no-insurance-limit`: Compare alerts against insurance-inclusive or base price
- `--only-cancelable` or `--no-only-cancelable`: Restrict to cancelable offers
- `--interval-seconds`: Base monitor interval
- `--recovery-delay-seconds`: Delay after a failed cycle
- `--jitter-min`: Minimum interval multiplier
- `--jitter-max`: Maximum interval multiplier
- `--timeout-ms`: Playwright timeout in milliseconds
- `--once`: Run exactly one cycle

## Environment Variables

Every CLI option has an environment-based default:

- `RCA_URL`
- `RCA_PRICE_LIMIT`
- `RCA_EMAIL_TO`
- `RCA_EMAIL`
- `RCA_EMAIL_FROM`
- `RCA_SMTP_HOST`
- `RCA_SMTP_PORT`
- `RCA_SMTP_USERNAME`
- `RCA_SMTP_PASSWORD`
- `RCA_HEADLESS`
- `RCA_INSURANCE_LIMIT`
- `RCA_ONLY_CANCELABLE`
- `RCA_INTERVAL_SECONDS`
- `RCA_RECOVERY_DELAY_SECONDS`
- `RCA_JITTER_MIN`
- `RCA_JITTER_MAX`
- `RCA_TIMEOUT_MS`
- `RCA_RUN_ONCE`

## Gmail Example

If you use Gmail, you typically need an app password, not your normal account password.

Example:

```bash
export RCA_EMAIL_FROM='your-account@gmail.com'
export RCA_SMTP_HOST='smtp.gmail.com'
export RCA_SMTP_PORT='587'
export RCA_SMTP_USERNAME='your-account@gmail.com'
export RCA_SMTP_PASSWORD='your-16-char-app-password'
```

## Troubleshooting

`playwright is required`

- Run `poetry install`

`browser executable doesn't exist`

- Run `poetry run playwright install chromium`

`SMTP configuration is incomplete`

- Set the SMTP environment variables listed above

`No cars found cheaper than ...`

- This is a normal result when no matching offer is below your threshold

`Monitoring cycle failed`

- Re-run with `--once --no-headless` to inspect the live browser flow visually

## Recreate The Environment From Scratch

If you deleted the environment, recreate it with:

```bash
poetry env use python3.12
poetry install
poetry run playwright install chromium
```

If you want to confirm the environment path:

```bash
poetry env info
```
