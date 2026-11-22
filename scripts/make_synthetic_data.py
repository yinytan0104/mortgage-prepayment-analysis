"""Generate FAKE data in the same file format as Freddie Mac's sample files.

This exists only so you can run and test the code before downloading the real
data. The rate path is a rough made-up shape and the borrowers are simulated.
Never present results from this data.

    python scripts/make_synthetic_data.py          # writes to data/synthetic/
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"
rng = np.random.default_rng(42)

START, END = pd.Period("2019-01", "M"), pd.Period("2025-12", "M")
VINTAGES = {2019: 4.2, 2021: 3.1, 2023: 6.7}  # rough avg note rate per loan year
N_LOANS = 4000
N_ORIG_COLS, N_SVCG_COLS = 32, 32


def fake_market_rates() -> pd.Series:
    """A made-up monthly 30-yr rate path: ~4.5% falling to ~2.8%, then up to ~7%."""
    months = pd.period_range(START, END, freq="M")
    t = np.arange(len(months))
    shape = np.interp(t, [0, 24, 36, 45, 58, 70, len(t) - 1], [4.5, 2.8, 3.1, 5.5, 7.4, 6.6, 6.3])
    return pd.Series(shape + rng.normal(0, 0.06, len(t)), index=months)


def hazard(incentive, age):
    """Monthly payoff probability: S-shaped in incentive, ramping up with age."""
    refi = 0.035 / (1 + np.exp(-3.0 * (incentive - 0.6)))
    turnover = 0.004
    ramp = np.minimum(1.0, age / 24)
    return (turnover + refi) * (0.3 + 0.7 * ramp)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    market = fake_market_rates()

    weekly = []
    for p, r in market.items():
        for d in pd.date_range(p.start_time, p.end_time, freq="W-THU"):
            weekly.append((d.strftime("%Y-%m-%d"), round(r + rng.normal(0, 0.03), 2)))
    pd.DataFrame(weekly, columns=["observation_date", "MORTGAGE30US"]).to_csv(
        OUT / "MORTGAGE30US.csv", index=False
    )

    for year, avg_rate in VINTAGES.items():
        orig_rows, svcg_rows = [], []
        for i in range(N_LOANS):
            loan_id = f"F{str(year)[2:]}Q1{i:07d}"
            first_pay = pd.Period(f"{year}-{rng.integers(1, 13):02d}", "M") + 1
            rate = round(max(2.0, rng.normal(avg_rate, 0.35)) * 8) / 8
            upb = int(rng.integers(120, 650) * 1000)
            o = [""] * N_ORIG_COLS
            o[0] = str(rng.integers(640, 820))
            o[1] = first_pay.strftime("%Y%m")
            o[9] = str(rng.integers(15, 48))
            o[10] = str(upb)
            o[11] = str(rng.integers(55, 97))
            o[12] = f"{rate:.3f}"
            o[16] = rng.choice(["CA", "TX", "FL", "NY", "NJ", "OR"])
            o[19] = loan_id
            o[20] = rng.choice(["P", "N", "C"])
            o[21] = "360"
            orig_rows.append("|".join(o))

            bal, monthly_rate = float(upb), rate / 1200
            pmt = upb * monthly_rate / (1 - (1 + monthly_rate) ** -360)
            period, age = first_pay, 1
            while period <= END:
                inc = rate - market.get(period - 1, market.iloc[-1])
                paid_off = rng.random() < hazard(inc, age)
                bal = max(0.0, bal - (pmt - bal * monthly_rate))
                s = [""] * N_SVCG_COLS
                s[0], s[1] = loan_id, period.strftime("%Y%m")
                s[2] = "0" if paid_off else f"{bal:.2f}"
                s[3], s[4] = "0", str(age)
                s[5] = str(360 - age)
                s[8] = "01" if paid_off else ""
                s[10] = f"{rate:.3f}"
                svcg_rows.append("|".join(s))
                if paid_off:
                    break
                period, age = period + 1, age + 1

        (OUT / f"sample_orig_{year}.txt").write_text("\n".join(orig_rows) + "\n")
        (OUT / f"sample_svcg_{year}.txt").write_text("\n".join(svcg_rows) + "\n")
        print(f"  {year}: {N_LOANS} loans, {len(svcg_rows):,} loan-months")
    print(f"Fake data written to {OUT}")


if __name__ == "__main__":
    main()
