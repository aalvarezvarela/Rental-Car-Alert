from __future__ import annotations

from dataclasses import dataclass


DEFAULT_ALLOWED_FUEL_POLICIES = frozenset(
    {
    "full/full",
    "lleno/lleno",
    "igual/igual",
    "like for like",
    "like/like",
    "same/same",
    }
)


def normalize_fuel_policy(raw_value: str) -> str:
    return " ".join(raw_value.lower().split())


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

    def is_fuel_policy_allowed(self, allowed_fuel_policies: frozenset[str]) -> bool:
        if not allowed_fuel_policies:
            return True
        normalized_policy = normalize_fuel_policy(self.fuel_policy)
        return normalized_policy in allowed_fuel_policies

    def alert_price(self, insurance_limit: bool) -> float | None:
        if insurance_limit:
            return self.insurance_price
        return self.price_without_insurance

    def qualifies_for_alert(
        self,
        limit: float,
        insurance_limit: bool,
        allowed_fuel_policies: frozenset[str],
    ) -> bool:
        alert_price = self.alert_price(insurance_limit)
        return (
            alert_price is not None
            and alert_price < limit
            and self.is_fuel_policy_allowed(allowed_fuel_policies)
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
