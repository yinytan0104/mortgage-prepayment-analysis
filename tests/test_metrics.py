import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prepay import metrics  # noqa: E402


def test_smm_to_cpr():
    assert metrics.smm_to_cpr(0) == 0
    assert metrics.smm_to_cpr(1) == 1
    # 1% a month is about 11.4% a year
    assert metrics.smm_to_cpr(0.01) == pytest.approx(0.1136, abs=1e-4)


def _toy():
    orig = pd.DataFrame(
        {
            "loan_id": ["A", "B"],
            "vintage": [2021, 2021],
            "orig_rate": [3.0, 6.0],
            "orig_upb": [100_000, 200_000],
            "credit_score": [750, 700],
            "orig_ltv": [80, 90],
        }
    )
    p = pd.PeriodIndex(["2023-01", "2023-02", "2023-03", "2023-01", "2023-02"], freq="M")
    perf = pd.DataFrame(
        {
            "loan_id": ["A", "A", "A", "B", "B"],
            "period": p,
            "current_upb": [99_000, 98_000, 97_000, 199_000, 0],
            "delinquency_status": ["0"] * 5,
            "loan_age": [1, 2, 3, 1, 2],
            "zero_balance_code": ["", "", "", "", "01"],
            "current_rate": [3.0, 3.0, 3.0, 6.0, 6.0],
        }
    )
    return orig, perf


def test_build_loan_months_and_cpr():
    orig, perf = _toy()
    lm = metrics.build_loan_months(orig, perf)
    assert len(lm) == 5
    assert lm["prepaid"].sum() == 1
    # B paid off in month 2; balance at start of that month was 199,000
    assert lm.loc[lm["prepaid"] == 1, "upb_start"].iloc[0] == 199_000
    t = metrics.cpr_by(lm, "period")
    feb = t[t["period"] == pd.Period("2023-02", "M")].iloc[0]
    assert feb["loans"] == 2 and feb["payoffs"] == 1
    assert feb["cpr"] == pytest.approx(metrics.smm_to_cpr(0.5))


def test_incentive_uses_lagged_rate():
    orig, perf = _toy()
    lm = metrics.build_loan_months(orig, perf)
    market = pd.Series([5.0, 4.0, 7.0], index=pd.PeriodIndex(["2022-12", "2023-01", "2023-02"], freq="M"))
    lm = metrics.add_incentive(lm, market, lag_months=1)
    row = lm[(lm["loan_id"] == "B") & (lm["period"] == pd.Period("2023-02", "M"))].iloc[0]
    assert row["market_rate"] == 4.0  # January's rate, used for February
    assert row["incentive"] == pytest.approx(2.0)


def test_lock_in_share():
    lm = pd.DataFrame(
        {
            "period": pd.PeriodIndex(["2023-01"] * 4, freq="M"),
            "incentive": [-3.0, -1.5, 0.0, 1.0],
            "note_rate": [3, 4, 6, 7],
            "market_rate": [6, 6, 6, 6],
        }
    )
    li = metrics.lock_in_share(lm, threshold=-1.0)
    assert li["share_locked_in"].iloc[0] == 0.5


def test_s_curve_is_increasing_on_synthetic_shape():
    rng = np.random.default_rng(0)
    n = 40_000
    inc = rng.uniform(-3, 3, n)
    p = 0.004 + 0.035 / (1 + np.exp(-3 * (inc - 0.6)))
    lm = pd.DataFrame(
        {
            "incentive": inc,
            "prepaid": (rng.random(n) < p).astype(int),
            "upb_start": 1.0,
            "prepaid_upb": 0.0,
        }
    )
    lm["prepaid_upb"] = lm["prepaid"] * 1.0
    sc = metrics.s_curve(lm, bin_width=1.0, lo=-3, hi=3, min_loans=100)
    assert sc["cpr"].iloc[-1] > sc["cpr"].iloc[0] * 3


def test_add_buckets():
    lm = pd.DataFrame({"note_rate": [2.99, 3.0, 6.74], "orig_upb": [150_000, 200_000, 500_000],
                       "credit_score": [690, 700, 790]})
    b = metrics.add_buckets(lm)
    assert list(b["rate_bucket"]) == [2.5, 3.0, 6.5]
    assert list(b["size_bucket"]) == ["Under $200K", "$200K to $400K", "$400K+"]
    assert list(b["credit_bucket"]) == ["Under 700", "700 to 759", "760+"]


def test_model_learns_incentive():
    from prepay import model

    rng = np.random.default_rng(1)
    n = 60_000
    periods = pd.period_range("2022-01", periods=24, freq="M")
    inc = rng.uniform(-3, 3, n)
    p = 0.002 + 0.03 / (1 + np.exp(-3 * (inc - 0.6)))
    lm = pd.DataFrame({
        "period": pd.PeriodIndex(rng.choice(periods, n), freq="M"),
        "incentive": inc,
        "loan_age": rng.integers(1, 60, n),
        "note_rate": rng.uniform(3, 7, n),
        "orig_upb": rng.uniform(1e5, 6e5, n),
        "credit_score": rng.uniform(620, 820, n),
        "orig_ltv": rng.uniform(50, 95, n),
        "orig_dti": rng.uniform(15, 45, n),
        "prepaid": (rng.random(n) < p).astype(int),
    })
    r = model.train_and_evaluate(lm, test_months=6)
    assert r["auc_gbm"] > 0.7
    assert r["importance"].iloc[0]["feature"] == "Refi incentive"
