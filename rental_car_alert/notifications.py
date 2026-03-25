from __future__ import annotations

import json
from html import escape

from rental_car_alert.models import CarOffer


def _format_price(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f} EUR"


def _format_price_compact(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}€"


def _offer_discount(offer: CarOffer, insurance_limit: bool, limit: float) -> float | None:
    chosen_price = offer.alert_price(insurance_limit)
    if chosen_price is None:
        return None
    return round(limit - float(chosen_price), 2)


def build_plaintext_email_body(
    offers: list[CarOffer],
    insurance_limit: bool,
    limit: float,
    url: str,
) -> str:
    lines = [
        f"{len(offers)} offer(s) below your alert threshold",
        f"Alert limit: {_format_price_compact(limit)}",
        "",
    ]

    for offer in offers:
        chosen_price = offer.alert_price(insurance_limit)
        if chosen_price is None:
            continue

        discount = _offer_discount(offer, insurance_limit, limit)
        price_summary = (
            f"{_format_price_compact(offer.insurance_price)} with insurance "
            f"({_format_price_compact(offer.price_without_insurance)} base price)"
            if offer.insurance_price is not None
            else f"{_format_price_compact(offer.price_without_insurance)} base price"
        )
        lines.append(
            f"{offer.model} | {offer.company}"
        )
        if discount is not None:
            lines.append(f"Saved vs limit: {_format_price_compact(discount)}")
        lines.append(f"Tracked price: {_format_price_compact(chosen_price)}")
        lines.append(f"Price summary: {price_summary}")
        lines.append(f"Pickup: {offer.pickup}")
        lines.append(f"Fuel: {offer.fuel_policy}")
        lines.append(f"Mileage: {offer.mileage_policy}")
        lines.append(f"Policy: {offer.refund_policy}")
        lines.append(f"Doors: {offer.doors}")
        lines.append("")

    lines.append(f"Open search: {url}")
    return "\n".join(lines)


def build_html_email_body(
    offers: list[CarOffer],
    insurance_limit: bool,
    limit: float,
    url: str,
) -> str:
    cards: list[str] = []

    for offer in offers:
        chosen_price = offer.alert_price(insurance_limit)
        if chosen_price is None:
            continue

        discount = _offer_discount(offer, insurance_limit, limit)
        cards.append(
            f"""
            <tr>
              <td style="padding:0 0 18px 0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:separate;border-spacing:0;background:#ffffff;border:1px solid #dbe4ea;border-radius:18px;overflow:hidden;">
                  <tr>
                    <td style="padding:22px 24px 8px 24px;">
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                        <tr>
                          <td style="font-family:Arial,sans-serif;font-size:22px;line-height:28px;font-weight:700;color:#16324f;">
                            {escape(offer.model)}
                          </td>
                          <td align="right" style="font-family:Arial,sans-serif;font-size:28px;line-height:32px;font-weight:800;color:#0d8a6a;white-space:nowrap;">
                            {_format_price(chosen_price)}
                          </td>
                        </tr>
                        <tr>
                          <td style="padding-top:4px;font-family:Arial,sans-serif;font-size:14px;line-height:20px;color:#4f6478;">
                            {escape(offer.company)}
                          </td>
                          <td align="right" style="padding-top:4px;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#7b8c9a;">
                            Base {_format_price(offer.price_without_insurance)}
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:0 24px 16px 24px;">
                      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                        <tr>
                          <td style="padding:0 8px 8px 0;">
                            <span style="display:inline-block;background:#eef7f4;color:#0d8a6a;border-radius:999px;padding:7px 11px;font-family:Arial,sans-serif;font-size:12px;font-weight:700;">
                              Save {_format_price(discount)}
                            </span>
                          </td>
                          <td style="padding:0 8px 8px 0;">
                            <span style="display:inline-block;background:#eef4fb;color:#28598a;border-radius:999px;padding:7px 11px;font-family:Arial,sans-serif;font-size:12px;font-weight:700;">
                              {escape(offer.fuel_policy)}
                            </span>
                          </td>
                          <td style="padding:0 8px 8px 0;">
                            <span style="display:inline-block;background:#fff6e8;color:#946200;border-radius:999px;padding:7px 11px;font-family:Arial,sans-serif;font-size:12px;font-weight:700;">
                              {escape(offer.doors)} doors
                            </span>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:0 24px 22px 24px;">
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;">
                        <tr>
                          <td width="50%" style="padding:10px 0;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#7b8c9a;border-top:1px solid #edf2f7;">Pickup</td>
                          <td width="50%" style="padding:10px 0;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#16324f;border-top:1px solid #edf2f7;">{escape(offer.pickup)}</td>
                        </tr>
                        <tr>
                          <td style="padding:10px 0;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#7b8c9a;border-top:1px solid #edf2f7;">Mileage</td>
                          <td style="padding:10px 0;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#16324f;border-top:1px solid #edf2f7;">{escape(offer.mileage_policy)}</td>
                        </tr>
                        <tr>
                          <td style="padding:10px 0;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#7b8c9a;border-top:1px solid #edf2f7;">Insurance</td>
                          <td style="padding:10px 0;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#16324f;border-top:1px solid #edf2f7;">{_format_price(offer.insurance_price)}</td>
                        </tr>
                        <tr>
                          <td style="padding:10px 0;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#7b8c9a;border-top:1px solid #edf2f7;">Policy</td>
                          <td style="padding:10px 0;font-family:Arial,sans-serif;font-size:13px;line-height:18px;color:#16324f;border-top:1px solid #edf2f7;">{escape(offer.refund_policy)}</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            """
        )

    return f"""
    <html>
      <body style="margin:0;padding:0;background:#edf3f8;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#edf3f8;">
          <tr>
            <td align="center" style="padding:28px 16px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:760px;border-collapse:separate;border-spacing:0;">
                <tr>
                  <td style="padding:0 0 18px 0;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:linear-gradient(135deg,#16324f 0%,#215a6d 55%,#0d8a6a 100%);border-radius:24px;overflow:hidden;">
                      <tr>
                        <td style="padding:30px 30px 24px 30px;font-family:Arial,sans-serif;color:#ffffff;">
                          <div style="font-size:12px;line-height:16px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;opacity:0.82;">Rental Car Alert</div>
                          <div style="padding-top:10px;font-size:32px;line-height:38px;font-weight:800;">{len(offers)} offer(s) below your limit</div>
                          <div style="padding-top:12px;font-size:16px;line-height:24px;max-width:520px;color:#dceef1;">
                            Fresh price drop detected. Clean summary below, with the tracked total and the savings against your {_format_price(limit)} alert threshold.
                          </div>
                          <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-top:20px;">
                            <tr>
                              <td style="padding:0 10px 10px 0;">
                                <span style="display:inline-block;background:rgba(255,255,255,0.14);color:#ffffff;border-radius:999px;padding:9px 14px;font-size:13px;font-weight:700;">
                                  Alert limit {_format_price(limit)}
                                </span>
                              </td>
                              <td style="padding:0 10px 10px 0;">
                                <span style="display:inline-block;background:rgba(255,255,255,0.14);color:#ffffff;border-radius:999px;padding:9px 14px;font-size:13px;font-weight:700;">
                                  {"Insurance price mode" if insurance_limit else "Base price mode"}
                                </span>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                {''.join(cards)}
                <tr>
                  <td style="padding-top:8px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#ffffff;border:1px solid #dbe4ea;border-radius:18px;">
                      <tr>
                        <td style="padding:24px 24px 28px 24px;font-family:Arial,sans-serif;">
                          <div style="font-size:18px;line-height:24px;font-weight:800;color:#16324f;">Open the live search</div>
                          <div style="padding-top:8px;font-size:14px;line-height:21px;color:#5d7285;">
                            Review the latest prices directly on DoYouSpain.
                          </div>
                          <div style="padding-top:18px;">
                            <a href="{escape(url, quote=True)}" style="display:inline-block;background:#16324f;color:#ffffff;text-decoration:none;border-radius:12px;padding:12px 18px;font-size:14px;font-weight:700;">
                              View search results
                            </a>
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def build_email_body(
    offers: list[CarOffer],
    insurance_limit: bool,
    limit: float,
    url: str,
) -> tuple[str, str]:
    return (
        build_plaintext_email_body(offers, insurance_limit, limit, url),
        build_html_email_body(offers, insurance_limit, limit, url),
    )


def serialize_alert_snapshot(
    offers: list[CarOffer],
    insurance_limit: bool,
) -> str:
    payload = [
        {
            "company": offer.company,
            "model": offer.model,
            "pickup": offer.pickup,
            "mileage_policy": offer.mileage_policy,
            "fuel_policy": offer.fuel_policy,
            "refund_policy": offer.refund_policy,
            "doors": offer.doors,
            "price_without_insurance": round(offer.price_without_insurance, 2),
            "insurance_price": round(offer.insurance_price, 2)
            if offer.insurance_price is not None
            else None,
            "alert_price": round(offer.alert_price(insurance_limit), 2)
            if offer.alert_price(insurance_limit) is not None
            else None,
        }
        for offer in offers
    ]
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)
