# Mortgage prepayment analysis: summary

- Loans analyzed: **300,000** (12,038,141 loan-months)
- Months covered: **2019-01 to 2026-06**

## Prepayment speed by loan year

| Loan year | Loans | Avg note rate | Lifetime CPR | Last 12 months CPR | Peak CPR (month) |
|---|---|---|---|---|---|
| 2019 | 50,000 | 4.24% | 19.7% | 6.9% | 47.3% (2021-03) |
| 2020 | 50,000 | 3.20% | 8.7% | 5.0% | 21.6% (2021-03) |
| 2021 | 50,000 | 2.97% | 4.5% | 4.9% | 6.7% (2026-06) |
| 2022 | 50,000 | 5.09% | 5.8% | 8.1% | 9.7% (2026-03) |
| 2023 | 50,000 | 6.74% | 10.5% | 16.1% | 23.3% (2025-10) |
| 2024 | 50,000 | 6.69% | 11.3% | 15.9% | 23.2% (2026-03) |

## Does the refi incentive matter?

| Borrower position | CPR | Loan-months |
|---|---|---|
| In the money (rate 1+ pt above market) | 31.9% | 843,744 |
| At the money (within 0.25 pt) | 8.0% | 1,560,775 |
| Out of the money (rate 1+ pt below market) | 5.0% | 6,281,336 |

## Rate lock-in

- Share of outstanding loans 1+ pt below market, latest month (2026-06): **55.1%**
- Peak: **95.4%** in 2022-11

## Method notes

- CPR = 1 - (1 - SMM)^12, where SMM = full payoffs / loans outstanding that month.
- Counts full payoffs only (zero balance code 01). Partial prepayments are not included.
- Payoffs include refinances and home sales. The data doesn't split them.
- Refi incentive = loan rate minus the Freddie Mac PMMS 30-year rate, lagged one month.
- Source: Freddie Mac Single-Family Loan-Level Dataset (sample files) and PMMS via FRED.
