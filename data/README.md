# Getting the data

Put everything in `data/raw/`. These files are ignored by git, so they won't get uploaded to GitHub.

## 1. Freddie Mac loan data (about 15 minutes)

1. Go to the [Single-Family Loan-Level Dataset page](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset).
2. Create a free account (they ask for a name, email, and to accept the terms of use).
3. Download the **Sample** files (not the full dataset, which is huge) for the years you want. I recommend **2019, 2021, and 2023**:
   - 2019: loans made around 4%, then a huge refi wave in 2020 and 2021
   - 2021: loans made around 3%, which became "locked in" when rates jumped
   - 2023: loans made around 6.5 to 7%, which can refinance if rates come down
4. Each year downloads as `sample_YYYY.zip`. Drop the zips into `data/raw/` as they are. The code reads the zip directly, or you can unzip them. Either way works.

Inside each zip:
- `sample_orig_YYYY.txt`: one row per loan (credit score, loan amount, interest rate, and so on)
- `sample_svcg_YYYY.txt`: one row per loan per month (balance, loan age, and whether it paid off)

## 2. Market mortgage rate (2 minutes)

1. Go to [FRED: MORTGAGE30US](https://fred.stlouisfed.org/series/MORTGAGE30US).
2. Click **Download** and choose **CSV**.
3. Save it as `data/raw/MORTGAGE30US.csv`.

## What data/raw should look like

```
data/raw/
    MORTGAGE30US.csv
    sample_2019.zip
    sample_2021.zip
    sample_2023.zip
```

Then run `python run_analysis.py` from the project folder.

## Terms of use

Freddie Mac's data has its own terms of use. Don't upload the raw files to GitHub. Sharing your charts and summary numbers is fine.
