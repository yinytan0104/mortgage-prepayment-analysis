"""Load Freddie Mac Single-Family Loan-Level sample files.

Freddie Mac publishes yearly sample files with no header row, pipe-delimited:
    sample_orig_YYYY.txt   one row per loan (origination data)
    sample_svcg_YYYY.txt   one row per loan per month (monthly performance)

They usually come zipped as sample_YYYY.zip. This module reads either the
.txt files or the .zip directly from data/raw/.

We only read the columns we need, by position, so small layout changes at the
end of the files between releases don't break anything. Column positions come
from Freddie Mac's "Single-Family Loan-Level Dataset General User Guide".
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pandas as pd

# Origination file: (position, name)
ORIG_COLS = {
    0: "credit_score",
    1: "first_payment_date",
    9: "orig_dti",
    10: "orig_upb",
    11: "orig_ltv",
    12: "orig_rate",
    16: "property_state",
    19: "loan_id",
    20: "loan_purpose",
    21: "orig_term",
}

# Monthly performance file: (position, name)
SVCG_COLS = {
    0: "loan_id",
    1: "period",
    2: "current_upb",
    3: "delinquency_status",
    4: "loan_age",
    8: "zero_balance_code",
    10: "current_rate",
}

# Zero balance code "01" = prepaid or matured (voluntary payoff).
# Other codes (02, 03, 09, 15, 96...) are defaults, sales, repurchases, etc.
PREPAY_CODE = "01"


def _read_pipe(handle, cols: dict[int, str]) -> pd.DataFrame:
    positions = sorted(cols)
    df = pd.read_csv(
        handle,
        sep="|",
        header=None,
        usecols=positions,
        dtype=str,
        engine="c",
    )
    df.columns = [cols[p] for p in positions]
    return df


# File names Freddie Mac has used over time, e.g.
#   sample_orig_2019.txt / sample_svcg_2019.txt   (sample files)
#   orig_2019Q1.txt / perf_2019Q1.txt             (newer naming, by quarter)
NAME_PATTERNS = {
    "orig": r"(sample_)?(historical_data_)?orig_{year}(Q[1-4])?\.txt$",
    "svcg": r"(sample_)?(historical_data_)?(svcg|perf|time)_{year}(Q[1-4])?\.txt$",
}


def _find_members(raw_dir: Path, kind: str, year: int) -> list:
    """Return file handles for every matching file, in .txt form or inside .zip files."""
    pat = re.compile(NAME_PATTERNS[kind].format(year=year), re.IGNORECASE)
    handles = []
    for f in sorted(raw_dir.rglob("*.txt")):
        if pat.search(f.name):
            handles.append(open(f, "rb"))
    if handles:
        return handles
    for z in sorted(raw_dir.rglob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            for name in sorted(zf.namelist()):
                if pat.search(Path(name).name):
                    handles.append(io.BytesIO(zf.read(name)))
    if not handles:
        raise FileNotFoundError(
            f"Couldn't find the {kind} file for {year} in {raw_dir}. "
            "See data/README.md for how to download the files."
        )
    return handles


def _read_all(raw_dir: Path, kind: str, year: int, cols: dict[int, str]) -> pd.DataFrame:
    parts = []
    for fh in _find_members(raw_dir, kind, year):
        with fh:
            parts.append(_read_pipe(fh, cols))
    return pd.concat(parts, ignore_index=True)


def available_years(raw_dir: str | Path) -> list[int]:
    """Find which vintages are sitting in data/raw."""
    raw_dir = Path(raw_dir)
    years = set()
    for p in raw_dir.rglob("*"):
        if p.suffix.lower() not in {".txt", ".zip"}:
            continue
        m = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", p.name)
        if m:
            years.add(int(m.group(0)))
    return sorted(years)


def load_origination(raw_dir: str | Path, year: int) -> pd.DataFrame:
    df = _read_all(Path(raw_dir), "orig", year, ORIG_COLS)
    for c in ["credit_score", "orig_dti", "orig_upb", "orig_ltv", "orig_rate", "orig_term"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Freddie uses 9999 / 999 as "not available"
    df.loc[df["credit_score"] >= 9999, "credit_score"] = pd.NA
    df.loc[df["orig_dti"] >= 999, "orig_dti"] = pd.NA
    df.loc[df["orig_ltv"] >= 999, "orig_ltv"] = pd.NA
    df["vintage"] = year
    return df


def load_performance(raw_dir: str | Path, year: int) -> pd.DataFrame:
    df = _read_all(Path(raw_dir), "svcg", year, SVCG_COLS)
    df["period"] = pd.PeriodIndex(df["period"].str.strip(), freq="M")
    for c in ["current_upb", "loan_age", "current_rate"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["zero_balance_code"] = df["zero_balance_code"].fillna("").str.strip().str.zfill(2)
    df.loc[df["zero_balance_code"] == "00", "zero_balance_code"] = ""
    return df


def load_vintages(raw_dir: str | Path, years: list[int] | None = None):
    """Load and stack origination + performance data for several vintages."""
    years = years or available_years(raw_dir)
    if not years:
        raise FileNotFoundError(f"No Freddie Mac sample files found in {raw_dir}.")
    origs, perfs = [], []
    for y in years:
        print(f"  loading {y} ...")
        origs.append(load_origination(raw_dir, y))
        perfs.append(load_performance(raw_dir, y))
    return pd.concat(origs, ignore_index=True), pd.concat(perfs, ignore_index=True)
