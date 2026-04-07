# Architecture Guide

## Overview

The application is organized as a small package:

- `rental_car_alert/config.py`: reads CLI flags and environment variables into typed dataclasses
- `rental_car_alert/cli.py`: application startup and logging
- `rental_car_alert/models.py`: core domain model for rental offers
- `rental_car_alert/parsers/doyouspain.py`: HTML parsing and price extraction
- `rental_car_alert/scrapers/doyouspain.py`: Playwright automation against the live site
- `rental_car_alert/notifications.py`: alert body generation and result snapshot serialization
- `rental_car_alert/services/email.py`: SMTP email delivery
- `rental_car_alert/services/monitor.py`: orchestration loop and deduplication logic

## Runtime Flow

### 1. Startup

`python -m rental_car_alert` calls [__main__.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/__main__.py), which delegates to [cli.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/cli.py).

`cli.py`:

- configures logging
- loads configuration from CLI and environment
- constructs the scraper, email client, and monitor
- starts the monitoring loop

### 2. Configuration

[config.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/config.py) converts runtime input into these immutable settings objects:

- `SearchSettings`
- `BrowserSettings`
- `EmailSettings`
- `MonitorSettings`
- `AppConfig`

This keeps runtime logic free of ad hoc environment lookups.

### 3. Browser Automation

[scrapers/doyouspain.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/scrapers/doyouspain.py) is responsible for live site interaction.

It:

- launches Chromium with Playwright
- opens the DoYouSpain homepage
- accepts cookies when the banner is present
- fills the pickup autocomplete and selects the first matching suggestion
- sets pickup and return dates
- submits the search form
- applies the `Full/Full` fuel filter
- optionally applies the cancelation filter
- captures the rendered results HTML

### 4. Parsing

[parsers/doyouspain.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/parsers/doyouspain.py) converts the rendered page into structured data.

It extracts:

- base price
- company
- pickup method
- mileage policy
- fuel policy
- refund policy
- model
- number of doors

Each parsed card becomes a `CarOffer`.

### 5. Insurance Price Resolution

The result list page is not enough on its own because the final insurance-inclusive price lives behind each offer's detail action.

For each offer whose base price is already below the threshold:

- the scraper clicks the matching results button
- Playwright waits for the detail popup to open
- the parser reads the insurance table or JavaScript fallback values
- the `insurance_price` is attached to the `CarOffer`

This keeps the scraper aligned with the live site flow instead of guessing at shared form actions or stale direct URLs.

### 6. Alert Filtering

[models.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/models.py) holds the logic for deciding whether an offer qualifies.

The key rules are:

- the relevant comparison price must be below the configured limit
- comparison can be base price or insurance-inclusive price depending on `insurance_limit`
- disallowed fuel policies are rejected

### 7. Deduplication

[notifications.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/notifications.py) serializes the alertable offers into a normalized snapshot.

[services/monitor.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/services/monitor.py) compares that snapshot to the previous cycle and only sends a new email when the result set changes.

When `RCA_SNAPSHOT_FILE` or `--snapshot-file` is configured, that snapshot is also persisted to disk. This lets scheduled GitHub Actions runs suppress duplicate emails even though each run starts a fresh Python process.

This prevents repeated notifications for the same matching offers.

### 8. Email Delivery

[services/email.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/services/email.py) sends the email through SMTP using `EmailMessage` and `smtplib`.

If SMTP settings are incomplete, the monitor logs a warning instead of crashing.

## Why This Structure

The project is split this way for practical reasons:

- browser logic is isolated from HTML parsing
- configuration is centralized and typed
- email delivery is isolated from monitoring logic
- the monitor orchestrates behavior without knowing page details
- the parser can evolve when the site markup changes without touching the mail or loop code

## Maintenance Notes

The most likely breakage point is DoYouSpain markup drift. If the site changes:

1. inspect the selectors in [scrapers/doyouspain.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/scrapers/doyouspain.py)
2. inspect the card and detail-page parsers in [parsers/doyouspain.py](/home/adrian_alvarez/Projects/Rental-Car-Alert/rental_car_alert/parsers/doyouspain.py)
3. run with `--once --no-headless` to watch the flow visually

The rest of the architecture should usually remain stable.
