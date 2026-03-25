from __future__ import annotations

from dataclasses import dataclass


ALLOWED_FUEL_POLICIES = {
    "full/full",
    "lleno/lleno",
    "igual/igual",
    "like for like",
    "like/like",
    "same/same",
}


@dataclass(slots=True)
class CarOffer:
    position: int
    price_without_insurance: float
    company: str
    pickup: str
    mileage_policy: str
    fuel_policy: str
    refund_policy: str
    model: str
    doors: str
    insurance_price: float | None = None

    def is_fuel_policy_allowed(self) -> bool:
        normalized_policy = " ".join(self.fuel_policy.lower().split())
        return normalized_policy in ALLOWED_FUEL_POLICIES

    def alert_price(self, insurance_limit: bool) -> float | None:
        if insurance_limit:
            return self.insurance_price
        return self.price_without_insurance

    def qualifies_for_alert(self, limit: float, insurance_limit: bool) -> bool:
        alert_price = self.alert_price(insurance_limit)
        return (
            alert_price is not None
            and alert_price < limit
            and self.is_fuel_policy_allowed()
        )

    def as_legacy_list(self) -> list[object]:
        values: list[object] = [
            self.price_without_insurance,
            self.company,
            self.pickup,
            self.mileage_policy,
            self.fuel_policy,
            self.refund_policy,
            self.model,
            self.doors,
        ]
        if self.insurance_price is not None:
            values.append(self.insurance_price)
        return values


@dataclass(slots=True, frozen=True)
class SearchRun:
    offers: list[CarOffer]
    results_url: str
