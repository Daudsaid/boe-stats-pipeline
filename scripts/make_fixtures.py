"""Generate offline test fixtures in the exact IADB CSV format.

These are SYNTHETIC test data, not real BoE values. Only the Bank Rate path
follows the real 2024-25 MPC decisions (so the decision models have realistic
events to work on); every other series is a seeded random walk around plausible
levels. Never use fixture output for analysis.

    uv run python scripts/make_fixtures.py
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "iadb"
START, END = date(2024, 1, 1), date(2025, 12, 31)

BANK_RATE_CHANGES = [  # effective date, new rate
    (date(2024, 1, 1), 5.25),
    (date(2024, 8, 1), 5.00),
    (date(2024, 11, 7), 4.75),
    (date(2025, 2, 6), 4.50),
    (date(2025, 5, 8), 4.25),
    (date(2025, 8, 7), 4.00),
    (date(2025, 12, 18), 3.75),
]


def business_days():
    d = START
    while d <= END:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def month_ends():
    d = START
    while d <= END:
        nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield nxt - timedelta(days=1)
        d = nxt


def bank_rate_on(d: date) -> float:
    return [r for eff, r in BANK_RATE_CHANGES if eff <= d][-1]


def write(code: str, rows: list[tuple[date, float]], decimals: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lines = [f"DATE,{code}"] + [f"{d.strftime('%d %b %Y')},{v:.{decimals}f}" for d, v in rows]
    (OUT / f"{code}.csv").write_text("\n".join(lines) + "\n")


def walk(start: float, vol: float, days: list[date], rng: random.Random, floor=0.0):
    v, out = start, []
    for d in days:
        v = max(floor, v + rng.gauss(0, vol))
        out.append((d, v))
    return out


def main() -> None:
    rng = random.Random(42)
    days = list(business_days())
    months = list(month_ends())

    write("IUDBEDR", [(d, bank_rate_on(d)) for d in days], 2)
    write("IUDSOIA", [(d, bank_rate_on(d) - 0.05 + rng.gauss(0, 0.004)) for d in days], 4)

    g5 = walk(4.0, 0.04, days, rng)
    write("IUDSNPY", g5, 4)
    write("IUDMNPY", [(d, v + 0.35 + rng.gauss(0, 0.02)) for d, v in g5], 4)
    write("IUDLNPY", [(d, v + 0.85 + rng.gauss(0, 0.02)) for d, v in g5], 4)

    write("XUDLUSS", walk(1.27, 0.005, days, rng, floor=1.0), 4)
    write("XUDLERS", walk(1.17, 0.003, days, rng, floor=1.0), 4)

    write("IUMBV34", [(m, bank_rate_on(m) + 0.15 + rng.gauss(0, 0.05)) for m in months], 2)
    write("IUMB482", [(m, bank_rate_on(m) + 0.75 + rng.gauss(0, 0.05)) for m in months], 2)

    m4, m4_rows = 2_950_000.0, []
    for m in months:
        m4 *= 1 + rng.gauss(0.003, 0.002)
        m4_rows.append((m, m4))
    write("LPMAUYN", m4_rows, 0)
    growth = [
        (m, (v / m4_rows[i - 12][1] - 1) * 100) for i, (m, v) in enumerate(m4_rows) if i >= 12
    ]
    write("LPMVQJW", growth, 1)

    print(f"wrote fixtures to {OUT}")


if __name__ == "__main__":
    main()
