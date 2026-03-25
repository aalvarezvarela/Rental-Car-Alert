from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup, Tag

from rental_car_alert.models import CarOffer


PRICE_SELECTORS = (
    "span.price.pr-euros.green.special-price",
    "span.price.pr-euros",
)
INSURANCE_LABELS = (
    "Alquiler + Seguro",
    "Rental + Insurance",
    "Rent + Insurance",
)


def normalize_text(raw_value: str) -> str:
    return " ".join(raw_value.split())


def parse_currency(raw_value: str) -> float:
    match = re.search(r"\d[\d.,]*", raw_value)
    if match is None:
        raise ValueError(f"Could not parse currency from: {raw_value!r}")

    number = match.group(0)
    if "," in number and "." in number:
        if number.rfind(",") > number.rfind("."):
            number = number.replace(".", "").replace(",", ".")
        else:
            number = number.replace(",", "")
    elif number.count(",") > 1:
        parts = number.split(",")
        number = "".join(parts[:-1]) + "." + parts[-1]
    elif number.count(".") > 1:
        parts = number.split(".")
        number = "".join(parts[:-1]) + "." + parts[-1]
    elif "," in number:
        number = number.replace(",", ".")

    return float(number)


def get_car_soups(soup: BeautifulSoup) -> list[Tag]:
    return list(soup.select("section.newcarlist.price-per-day article"))


def get_car_price(car: Tag) -> float:
    for selector in PRICE_SELECTORS:
        element = car.select_one(selector)
        if element is not None:
            return parse_currency(element.get_text(" ", strip=True))
    raise ValueError("Unable to locate a price in the offer card.")


def _get_text_or_default(car: Tag, selector: str, default: str = "Unknown") -> str:
    element = car.select_one(selector)
    if element is None:
        return default
    return normalize_text(element.get_text(" ", strip=True)) or default


def _extract_detail_request(car: Tag) -> tuple[str | None, str | None]:
    button = car.select_one('input[name^="coche"]')
    if button is None or not button.has_attr("onclick"):
        return None, None

    match = re.search(r"submitNext\('([^']+)',\s*'([^']+)'", button["onclick"])
    if match is None:
        return None, None
    return match.group(1), match.group(2)


def parse_offer_card(car: Tag, position: int) -> CarOffer:
    company = _get_text_or_default(car, "span.cl--car-rent-info", "Unknown")
    company_logo = car.select_one(".cl--car-rent-logo img")
    if company_logo is not None and company_logo.has_attr("alt"):
        company = normalize_text(company_logo["alt"])

    refund_policy = _get_text_or_default(car, "ul.cl--interest", "Not Refundable")
    if len(refund_policy) < 3:
        refund_policy = "Not Refundable"
    detail_action, detail_code = _extract_detail_request(car)

    return CarOffer(
        position=position,
        price_without_insurance=get_car_price(car),
        company=company,
        pickup=_get_text_or_default(car, "li.tooltipBlanco.serv.sc-airport"),
        mileage_policy=_get_text_or_default(
            car,
            "li.tooltipBlanco.serv.sc-mileage.sc-green",
        ),
        fuel_policy=_get_text_or_default(car, "span.udl-block"),
        refund_policy=refund_policy,
        model=_get_text_or_default(car, "div.cl--name h2"),
        doors=_get_text_or_default(car, "li.tooltipBlanco.serv.sc-doors"),
        detail_action=detail_action,
        detail_code=detail_code,
    )


def get_info_car(car: Tag, n: int, limit: float | None = None) -> list[object]:
    del limit
    return parse_offer_card(car, n).as_legacy_list()


def parse_offers(soup: BeautifulSoup) -> list[CarOffer]:
    return [parse_offer_card(car, index) for index, car in enumerate(get_car_soups(soup))]


def _extract_insurance_cell_values(cells: Iterable[Tag]) -> float | None:
    for cell in cells:
        cell_text = normalize_text(cell.get_text(" ", strip=True))
        if any(label in cell_text for label in INSURANCE_LABELS):
            return parse_currency(cell_text)
    return None


def get_insurance_price(newsoup: BeautifulSoup, original_price: float) -> float | str:
    insurance_value = _extract_insurance_cell_values(
        newsoup.select('td[data-for="insurance"]')
    )
    if insurance_value is not None:
        return insurance_value

    raw_html = str(newsoup)
    c_aux_match = re.search(r"var cAux = ([0-9.]+);", raw_html)
    i_aux_match = re.search(r"var iAux = ([0-9.]+);", raw_html)

    insurance_c = float(c_aux_match.group(1)) if c_aux_match else 0.0
    insurance_i = float(i_aux_match.group(1)) if i_aux_match else 0.0

    if insurance_c > 0:
        return original_price + insurance_c
    if insurance_i > 0:
        return original_price + insurance_i
    return "Could not find it"
