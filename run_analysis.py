"""Run the whole analysis.

    python run_analysis.py                     # real data in data/raw, writes to outputs/
    python run_analysis.py --years 2019 2021 2023
    python run_analysis.py --synthetic         # fake data, to test the code
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from prepay import load, metrics, plots, rates, report  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Mortgage prepayment analysis on Freddie Mac loan data")
    ap.add_argument("--raw-dir", default=None, help="folder with Freddie Mac sample files (default data/raw)")
    ap.add_argument("--rates", default=None, help="FRED MORTGAGE30US csv (default <raw-dir>/MORTGAGE30US.csv)")
    ap.add_argument("--years", nargs="*", type=int, help="loan years to include (default: all found)")
    ap.add_argument("--out", default=None, help="output folder (default outputs/)")
    ap.add_argument("--lag", type=int, default=1, help="months to lag the market rate (default 1)")
    ap.add_argument("--lock-in-threshold", type=float, default=-1.0)
    ap.add_argument("--synthetic", action="store_true", help="use data/synthetic instead of real data")
    ap.add_argument("--skip-model", action="store_true", help="skip the prediction model (faster)")
    ap.add_argument("--test-months", type=int, default=12, help="months held out to test the model")
    args = ap.parse_args()

    if args.synthetic:
        raw_dir = Path(args.raw_dir or ROOT / "data" / "synthetic")
        out_dir = Path(args.out or ROOT / "outputs_synthetic")
    else:
        raw_dir = Path(args.raw_dir or ROOT / "data" / "raw")
        out_dir = Path(args.out or ROOT / "outputs")
    rates_path = Path(args.rates or raw_dir / "MORTGAGE30US.csv")
    out_dir.mkdir(parents=True, exist_ok=True)
    note = "SYNTHETIC DATA, for testing only" if args.synthetic else \
        "Source: Freddie Mac Single-Family Loan-Level Dataset (sample), Freddie Mac PMMS via FRED"

    print(f"Reading loan data from {raw_dir}")
    orig, perf = load.load_vintages(raw_dir, args.years)
    print(f"Reading market rates from {rates_path}")
    market = rates.load_market_rates(rates_path)

    print("Building loan-month table ...")
    lm = metrics.build_loan_months(orig, perf)
    lm = metrics.add_incentive(lm, market, lag_months=args.lag)
    lm = metrics.add_buckets(lm)

    print("Calculating prepayment speeds ...")
    vt = metrics.monthly_cpr_by_vintage(lm)
    sc = metrics.s_curve(lm)
    scv = metrics.s_curve(lm, by_vintage=True, min_loans=300)
    sa = metrics.cpr_by_loan_age(lm)
    li = metrics.lock_in_share(lm, threshold=args.lock_in_threshold)
    rb = metrics.cpr_by_rate_bucket(lm)
    by_size = metrics.s_curve_by(lm, "size_bucket")
    by_credit = metrics.s_curve_by(lm, "credit_bucket")

    tables = out_dir / "tables"
    tables.mkdir(exist_ok=True)
    vt.to_csv(tables / "cpr_by_vintage_month.csv", index=False)
    sc.to_csv(tables / "s_curve.csv", index=False)
    scv.to_csv(tables / "s_curve_by_vintage.csv", index=False)
    sa.to_csv(tables / "cpr_by_loan_age.csv", index=False)
    li.to_csv(tables / "lock_in_share.csv", index=False)
    rb.to_csv(tables / "cpr_by_loan_rate.csv", index=False)
    by_size.to_csv(tables / "s_curve_by_loan_size.csv", index=False)
    by_credit.to_csv(tables / "s_curve_by_credit_score.csv", index=False)

    print("Drawing charts ...")
    plots.plot_cpr_over_time(vt, market, out_dir, note)
    plots.plot_s_curve(sc, out_dir, note)
    plots.plot_s_curve_by_vintage(scv, out_dir, note)
    plots.plot_lock_in(li, out_dir, args.lock_in_threshold, note)
    plots.plot_seasoning(sa, out_dir, note)
    last_period = lm["period"].max()
    market_now = market.get(last_period, market.iloc[-1])
    plots.plot_cpr_by_rate(rb, market_now, out_dir, note)
    plots.plot_s_curve_by_size(by_size, metrics.SIZE_LABELS, out_dir, note)
    plots.plot_s_curve_by_credit(by_credit, metrics.CREDIT_LABELS, out_dir, note)

    model_results = None
    if not args.skip_model:
        print("Training prediction model (a few minutes) ...")
        from prepay import model
        model_results = model.train_and_evaluate(lm, test_months=args.test_months)
        model_results["by_month"].to_csv(tables / "model_by_month.csv", index=False)
        model_results["by_incentive"].to_csv(tables / "model_by_incentive.csv", index=False)
        model_results["importance"].to_csv(tables / "model_feature_importance.csv", index=False)
        plots.plot_model_by_month(model_results["by_month"], out_dir, note)
        plots.plot_model_by_incentive(model_results["by_incentive"], out_dir, note)
        plots.plot_feature_importance(model_results["importance"], out_dir, note)

    h = report.headline_numbers(lm, vt, li)
    h["model"] = model_results
    h["rate_buckets"] = rb
    h["market_now"] = market_now
    h["by_size_in_money"] = report.split_in_money(lm, "size_bucket", metrics.SIZE_LABELS)
    h["by_credit_in_money"] = report.split_in_money(lm, "credit_bucket", metrics.CREDIT_LABELS)
    h["by_vintage"].to_csv(tables / "vintage_summary.csv", index=False)
    path = report.write_summary(h, out_dir, synthetic=args.synthetic)
    print(f"\nDone. Charts, tables, and {path.name} are in {out_dir}")


if __name__ == "__main__":
    main()
