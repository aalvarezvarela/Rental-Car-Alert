from __future__ import annotations

import unittest

from bs4 import BeautifulSoup

from rental_car_alert.parsers.doyouspain import get_insurance_price


class GetInsurancePriceTests(unittest.TestCase):
    def test_adds_non_online_charges_to_insurance_price(self) -> None:
        soup = BeautifulSoup(
            """
            <span id="precioTotalValue">125,49</span>
            <span id="onlinePrecioValue">106,95</span>
            <table>
                <td data-for="insurance">
                    <strong>145,70 €</strong>
                    <small>Alquiler + Seguro</small>
                </td>
            </table>
            """,
            features="lxml",
        )

        self.assertAlmostEqual(get_insurance_price(soup, 106.95), 164.24)

    def test_uses_destination_price_when_total_breakdown_is_unavailable(self) -> None:
        soup = BeautifulSoup(
            """
            <span id="precioDestinoValue">19,04</span>
            <table>
                <td data-for="insurance">
                    <strong>149,00 €</strong>
                    <small>Alquiler + Seguro</small>
                </td>
            </table>
            """,
            features="lxml",
        )

        self.assertAlmostEqual(get_insurance_price(soup, 110.25), 168.04)

    def test_adds_javascript_insurance_price_to_explicit_total(self) -> None:
        soup = BeautifulSoup(
            """
            <span id="precioTotalValue">125,49</span>
            <script>var iAux = 38.75; var cAux = 0.00;</script>
            """,
            features="lxml",
        )

        self.assertAlmostEqual(get_insurance_price(soup, 106.95), 164.24)

    def test_preserves_legacy_insurance_value_without_total_breakdown(self) -> None:
        soup = BeautifulSoup(
            """
            <table>
                <td data-for="insurance">
                    <strong>145,70 €</strong>
                    <small>Alquiler + Seguro</small>
                </td>
            </table>
            """,
            features="lxml",
        )

        self.assertAlmostEqual(get_insurance_price(soup, 106.95), 145.70)


if __name__ == "__main__":
    unittest.main()
