"""Registry of Bank of England IADB series this pipeline ingests.

Adding a series = adding one entry here. Everything downstream (dlt resource,
dbt staging) is driven by this list, so no other Python change is needed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Frequency = Literal["daily", "monthly"]


@dataclass(frozen=True)
class Series:
    code: str
    name: str
    description: str
    frequency: Frequency
    unit: str
    category: str

    def as_row(self) -> dict:
        return asdict(self)


SERIES: tuple[Series, ...] = (
    # --- Policy & money-market rates -------------------------------------
    Series("IUDBEDR", "bank_rate", "Official Bank Rate", "daily", "percent", "policy_rate"),
    Series(
        "IUDSOIA",
        "sonia",
        "Sterling Overnight Index Average (SONIA)",
        "daily",
        "percent",
        "money_market",
    ),
    # --- Gilt nominal par yields (VRP model) ------------------------------
    Series(
        "IUDSNPY", "gilt_5y", "Nominal par yield, 5 year gilt", "daily", "percent", "gilt_yield"
    ),
    Series(
        "IUDMNPY", "gilt_10y", "Nominal par yield, 10 year gilt", "daily", "percent", "gilt_yield"
    ),
    Series(
        "IUDLNPY", "gilt_20y", "Nominal par yield, 20 year gilt", "daily", "percent", "gilt_yield"
    ),
    # --- FX spot (foreign currency per GBP) -------------------------------
    Series(
        "XUDLUSS", "gbp_usd", "Spot exchange rate, US$ into Sterling", "daily", "usd_per_gbp", "fx"
    ),
    Series(
        "XUDLERS", "gbp_eur", "Spot exchange rate, Euro into Sterling", "daily", "eur_per_gbp", "fx"
    ),
    # --- Quoted household mortgage rates ---------------------------------
    Series(
        "IUMBV34",
        "mortgage_2y_75ltv",
        "Quoted mortgage rate, 2y fixed, 75% LTV",
        "monthly",
        "percent",
        "mortgage_rate",
    ),
    Series(
        "IUMB482",
        "mortgage_2y_90ltv",
        "Quoted mortgage rate, 2y fixed, 90% LTV",
        "monthly",
        "percent",
        "mortgage_rate",
    ),
    # --- Broad money ------------------------------------------------------
    Series(
        "LPMAUYN",
        "m4_outstanding",
        "M4 amounts outstanding, seasonally adjusted",
        "monthly",
        "gbp_millions",
        "money_supply",
    ),
    Series(
        "LPMVQJW",
        "m4_growth_12m",
        "M4 12-month growth rate, seasonally adjusted",
        "monthly",
        "percent",
        "money_supply",
    ),
)

SERIES_BY_CODE: dict[str, Series] = {s.code: s for s in SERIES}


def get_series(codes: list[str] | None = None) -> list[Series]:
    """Return registry entries, optionally filtered to the given codes."""
    if not codes:
        return list(SERIES)
    unknown = sorted(set(codes) - SERIES_BY_CODE.keys())
    if unknown:
        raise ValueError(f"Unknown series code(s): {unknown}. Known: {sorted(SERIES_BY_CODE)}")
    return [SERIES_BY_CODE[c] for c in codes]
