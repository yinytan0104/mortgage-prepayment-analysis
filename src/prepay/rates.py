"""Load the market mortgage rate (Freddie Mac PMMS 30-year fixed, weekly).

Easiest source: FRED series MORTGAGE30US, downloaded as CSV from
https://fred.stlouisfed.org/series/MORTGAGE30US  ("Download" > CSV).

The CSV has two columns: a date column (named "observation_date" in newer
downloads, "DATE" in older ones) and MORTGAGE30US. We turn the weekly numbers
into a monthly average.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_market_rates(path: str | Path) -> pd.Series:
    df = pd.read_csv(path)
    date_col = next(c for c in df.columns if c.lower() in {"observation_date", "date"})
    rate_col = next(c for c in df.columns if c != date_col)
    df[date_col] = pd.to_datetime(df[date_col])
    df[rate_col] = pd.to_numeric(df[rate_col], errors="coerce")  # FRED uses "." for missing
    df = df.dropna(subset=[rate_col])
    monthly = df.groupby(df[date_col].dt.to_period("M"))[rate_col].mean()
    monthly.index.name = "period"
    monthly.name = "market_rate"
    return monthly
