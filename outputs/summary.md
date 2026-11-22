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

## Prepayment speed by loan rate (last 12 months)

Window: 2025-07 to 2026-06. Market 30-yr rate in the latest month: about 6.49%.

| Loan rate bucket | CPR | Loan-months |
|---|---|---|
| 1.5% to 1.99% | 4.5% | 6,515 |
| 2.0% to 2.49% | 5.2% | 67,548 |
| 2.5% to 2.99% | 4.4% | 415,632 |
| 3.0% to 3.49% | 5.0% | 329,016 |
| 3.5% to 3.99% | 5.9% | 226,658 |
| 4.0% to 4.49% | 6.8% | 95,512 |
| 4.5% to 4.99% | 6.9% | 118,139 |
| 5.0% to 5.49% | 7.1% | 94,834 |
| 5.5% to 5.99% | 8.0% | 226,457 |
| 6.0% to 6.49% | 10.0% | 229,366 |
| 6.5% to 6.99% | 15.6% | 420,441 |
| 7.0% to 7.49% | 23.2% | 170,260 |
| 7.5% to 7.99% | 26.2% | 97,596 |
| 8.0% to 8.49% | 29.3% | 11,518 |
| 8.5% to 8.99% | 31.1% | 2,811 |

## Does the incentive effect change by loan size?

| Loan size | CPR, 1+ pt in the money | CPR, 1+ pt out of the money |
|---|---|---|
| Under $200K | 22.5% (412,334) | 6.1% (2,089,529) |
| $200K to $400K | 38.2% (324,958) | 4.7% (2,903,087) |
| $400K+ | 44.7% (106,452) | 3.7% (1,288,720) |

Loan-months in parentheses.

## Does the incentive effect change by credit score?

| Credit score | CPR, 1+ pt in the money | CPR, 1+ pt out of the money |
|---|---|---|
| Under 700 | 24.6% (208,032) | 5.9% (887,185) |
| 700 to 759 | 31.3% (327,292) | 4.9% (2,177,687) |
| 760+ | 37.1% (308,181) | 4.7% (3,215,377) |

Loan-months in parentheses.

## Method notes

- CPR = 1 - (1 - SMM)^12, where SMM = full payoffs / loans outstanding that month.
- Counts full payoffs only (zero balance code 01). Partial prepayments are not included.
- Payoffs include refinances and home sales. The data doesn't split them.
- Refi incentive = loan rate minus the Freddie Mac PMMS 30-year rate, lagged one month.
- Loan rate buckets use the loan's note rate. MBS pool coupons run about 0.5 to 0.75 pt lower.
- Source: Freddie Mac Single-Family Loan-Level Dataset (sample files) and PMMS via FRED.
