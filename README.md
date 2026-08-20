# Subscription Retention & Churn Analytics

Cohort retention analysis for a subscription business — SQL (recursive CTEs,
window functions, self-referencing date logic) and a live interactive dashboard
with a cohort retention heatmap.

**🔗 Live dashboard:** https://github.com/nashrahfatma/cohort-retention-dashboard.git
*(enable in Settings → Pages → deploy from `main` branch → root)*

> **Note on data:** This project uses a synthetically generated subscription
> dataset (13,960 users, 30 monthly signup cohorts, Jan 2024–Aug 2026) — not a
> live production database. Churn behavior is grounded in real, publicly
> reported 2026 subscription-industry benchmarks (Recurly / ChurnTools): B2C
> subscription apps average 5–8% monthly churn, with faster churn in early
> "onboarding" months that stabilizes over time, and annual-plan subscribers
> churning far less often per month than monthly-plan subscribers — both
> well-documented industry patterns. Generated with `python/generate_data.py`.

## Why this problem
Customer retention is one of the most in-demand analytics skills right now —
churn is the single biggest lever on revenue for any subscription business
(SaaS, OTT, edtech, gym memberships). This project answers the question every
subscription business asks: **"Of the people who signed up in a given month,
how many are still with us N months later — and why does it vary?"**

## Tech Stack
- **SQL (SQLite)** — recursive CTEs, window functions, self-referencing date
  arithmetic for cohort retention calculation
- **Python (pandas, numpy)** — data generation and pipeline orchestration
- **HTML / CSS / JavaScript (Chart.js)** — live interactive dashboard with a
  cohort heatmap grid

## Repo Structure
```
├── index.html                 # Live interactive dashboard (GitHub Pages entry point)
├── python/
│   ├── generate_data.py       # Generates data/subscriptions.csv
│   ├── load_and_clean.py      # Loads into SQLite, runs cleaning
│   └── export_summaries.py    # Runs cohort queries, exports output/*.csv
├── sql/
│   ├── 01_data_cleaning.sql       # Dedup + missing-city handling
│   └── 02_cohort_analysis.sql     # Cohort retention table + 4 more analysis queries
└── data/                       # Generated input CSV (subscription records)
```

## Data Cleaning
- Removed duplicate `user_id` rows using `ROW_NUMBER() OVER (PARTITION BY ...)`
- Handled missing `city` values (~1.5% of rows) → labeled explicitly as
  `Unknown` rather than dropped, to preserve valid churn/plan data

## Key SQL Techniques Demonstrated
- **Recursive CTE** (`WITH RECURSIVE`) to generate a month-offset series (0–20)
  for the cohort table — SQLite has no built-in date-series generator
- **Cohort retention table**: for each signup month, the % of users still
  active at month 0, 1, 2, ... N — computed via `CROSS JOIN` + date arithmetic,
  the classic SaaS/subscription cohort analysis pattern
- `ROW_NUMBER() OVER (PARTITION BY user_id ...)` for deduplication
- Conditional aggregation (`SUM(CASE WHEN ...)`) for churn-rate calculations

## Key Insights
1. **Steepest drop-off is Month 0 → 1**: retention falls from 100% to 89.6% in
   the first month alone — onboarding/first-month engagement is the single
   biggest lever.
2. **Annual plans retain 3.4× better than Monthly** (16.0% vs 54.2% lifetime
   churn) — worth incentivizing the annual-plan upgrade path more aggressively.
3. **Retention curve flattens after month ~9** — users who reach 9 months
   rarely churn afterward, a "loyalty threshold" worth targeting.
4. **City-level churn is fairly uniform** (39.5%–44.9%) — unlike plan type,
   geography isn't a strong churn driver here.

## How to Reproduce
```bash
pip install -r requirements.txt

python python/generate_data.py       # → data/subscriptions.csv
python python/load_and_clean.py      # → sql/cohort_analytics.db (cleaned)
python python/export_summaries.py    # → output/*.csv
```

`index.html` needs no build step — open it directly in a browser, or serve it
via GitHub Pages.
