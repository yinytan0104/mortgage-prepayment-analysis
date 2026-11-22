"""Predict whether a loan pays off next month.

Each row is one loan in one month. The target is 1 if the loan paid off in
full that month (zero balance code 01), else 0. The model sees what a trader
would know at the start of that month: the refi incentive, the loan's age and
rate, its size, and the borrower's credit score, loan-to-value and
debt-to-income at origination, plus the calendar month (home sales are
seasonal).

Validation is out-of-time: the model trains on earlier months and is scored on
the most recent months it has never seen. That is how a prepayment model is
actually used, and it is a much tougher test than a random split.

Two models are compared:
    * Logistic regression: a simple, explainable baseline
    * Gradient boosting (scikit-learn HistGradientBoostingClassifier): picks up
      the S-curve shape and interactions (for example, big loans reacting more
      to the same incentive) without hand-built features

Scoring:
    * AUC: how well the model ranks loans that pay off above loans that don't
    * Predicted vs actual CPR, month by month and by incentive bucket: whether
      the model gets the overall speed right, which is what matters for MBS
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .metrics import smm_to_cpr

FEATURES = [
    "incentive",
    "loan_age",
    "note_rate",
    "log_loan_size",
    "credit_score",
    "orig_ltv",
    "orig_dti",
    "calendar_month",
]

FEATURE_NAMES = {
    "incentive": "Refi incentive",
    "loan_age": "Loan age",
    "note_rate": "Loan rate",
    "log_loan_size": "Loan size",
    "credit_score": "Credit score",
    "orig_ltv": "Loan-to-value",
    "orig_dti": "Debt-to-income",
    "calendar_month": "Calendar month",
}


def make_features(lm: pd.DataFrame) -> pd.DataFrame:
    keep = ["period", "prepaid", "incentive", "loan_age", "note_rate", "orig_upb",
            "credit_score", "orig_ltv", "orig_dti"]
    d = lm.loc[lm["incentive"].notna(), [c for c in keep if c in lm.columns]].copy()
    d["log_loan_size"] = np.log(d["orig_upb"].clip(lower=1))
    d["calendar_month"] = d["period"].dt.month
    for c in ["credit_score", "orig_ltv", "orig_dti"]:
        if c not in d:
            d[c] = np.nan
        d[c] = pd.to_numeric(d[c], errors="coerce").astype(float)
    return d


def split_by_time(d: pd.DataFrame, test_months: int = 12):
    cutoff = d["period"].max() - test_months
    train = d[d["period"] <= cutoff]
    test = d[d["period"] > cutoff]
    return train, test, cutoff


def _sample(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    return df if len(df) <= n else df.sample(n, random_state=seed)


def train_and_evaluate(lm: pd.DataFrame, test_months: int = 12, max_train_rows: int = 3_000_000,
                       seed: int = 42) -> dict:
    d = make_features(lm)
    train, test, cutoff = split_by_time(d, test_months)
    if len(train) == 0 or len(test) == 0:
        raise ValueError("Not enough months of data to split into train and test.")
    tr = _sample(train, max_train_rows, seed)
    X_tr, y_tr = tr[FEATURES], tr["prepaid"]
    X_te, y_te = test[FEATURES], test["prepaid"]

    print(f"    training on {len(tr):,} loan-months (through {cutoff}), "
          f"testing on {len(test):,} loan-months after that")

    logit = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          LogisticRegression(max_iter=500))
    logit.fit(X_tr, y_tr)

    gbm = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=200,
        l2_regularization=1.0, early_stopping=True, validation_fraction=0.1,
        random_state=seed,
    )
    gbm.fit(X_tr, y_tr)

    test = test.copy()
    test["p_logit"] = logit.predict_proba(X_te)[:, 1]
    test["p_gbm"] = gbm.predict_proba(X_te)[:, 1]

    results = {
        "cutoff": str(cutoff),
        "test_start": str(cutoff + 1),
        "test_end": str(test["period"].max()),
        "n_train": len(tr),
        "n_test": len(test),
        "auc_logit": roc_auc_score(y_te, test["p_logit"]),
        "auc_gbm": roc_auc_score(y_te, test["p_gbm"]),
        "actual_cpr": smm_to_cpr(y_te.mean()),
        "pred_cpr_logit": smm_to_cpr(test["p_logit"].mean()),
        "pred_cpr_gbm": smm_to_cpr(test["p_gbm"].mean()),
    }

    # Month by month: actual vs predicted CPR
    g = test.groupby("period")
    results["by_month"] = pd.DataFrame({
        "actual_cpr": smm_to_cpr(g["prepaid"].mean()),
        "pred_cpr_logit": smm_to_cpr(g["p_logit"].mean()),
        "pred_cpr_gbm": smm_to_cpr(g["p_gbm"].mean()),
        "loans": g.size(),
    }).reset_index()

    # By incentive bucket: does the model get the S-curve right?
    test["incentive_mid"] = (np.floor(test["incentive"].clip(-3, 2.999) / 0.5) * 0.5 + 0.25).round(2)
    g = test.groupby("incentive_mid")
    by_inc = pd.DataFrame({
        "actual_cpr": smm_to_cpr(g["prepaid"].mean()),
        "pred_cpr_logit": smm_to_cpr(g["p_logit"].mean()),
        "pred_cpr_gbm": smm_to_cpr(g["p_gbm"].mean()),
        "loans": g.size(),
    }).reset_index()
    results["by_incentive"] = by_inc[by_inc["loans"] >= 1000]

    # Which features matter most (permutation importance on a test sample, AUC drop)
    imp_sample = _sample(test, 300_000, seed)
    pi = permutation_importance(gbm, imp_sample[FEATURES], imp_sample["prepaid"], scoring="roc_auc",
                                n_repeats=3, random_state=seed)
    results["importance"] = (
        pd.DataFrame({"feature": [FEATURE_NAMES[f] for f in FEATURES], "auc_drop": pi.importances_mean})
        .sort_values("auc_drop", ascending=False)
        .reset_index(drop=True)
    )
    return results
