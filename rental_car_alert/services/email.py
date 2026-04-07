from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from rental_car_alert.config import EmailSettings

LOGGER = logging.getLogger(__name__)


class EmailClient:
    def __init__(self, settings: EmailSettings) -> None:
        self._settings = settings

    def _missing_fields(self) -> list[str]:
        fields = {
            "recipient": self._settings.recipient,
            "sender": self._settings.sender,
            "smtp_host": self._settings.smtp_host,
            "smtp_port": self._settings.smtp_port,
            "smtp_username": self._settings.smtp_username,
            "smtp_password": self._settings.smtp_password,
        }
        return [
            name
            for name, value in fields.items()
            if value is None or (isinstance(value, str) and not value.strip())
        ]

    @property
    def is_configured(self) -> bool:
        return not self._missing_fields()

    def send(self, subject: str, text_body: str, html_body: str | None = None) -> bool:
        if not self.is_configured:
            LOGGER.warning(
                "SMTP configuration is incomplete; missing: %s. Skipping email delivery.",
                ", ".join(self._missing_fields()),
            )
            return False

        message = EmailMessage()
        message["From"] = self._settings.sender
        message["To"] = self._settings.recipient
        message["Subject"] = subject
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP(
                self._settings.smtp_host,
                self._settings.smtp_port,
                timeout=30,
            ) as connection:
                connection.ehlo()
                connection.starttls()
                connection.login(
                    self._settings.smtp_username,
                    self._settings.smtp_password,
                )
                connection.send_message(message)
        except Exception:
            LOGGER.exception("Failed to send alert email.")
            return False

        LOGGER.info("Alert email sent to %s.", self._settings.recipient)
        return True
