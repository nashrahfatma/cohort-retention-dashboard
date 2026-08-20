"""
Runs the cohort analysis queries and exports summary CSVs used by the dashboard.
Run from repo root: python python/export_summaries.py
"""
import sqlite3
import pandas as pd
import os

DB_PATH = "sql/cohort_analytics.db"
OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)
CURRENT_DATE = "2026-08-01"

conn = sqlite3.connect(DB_PATH)

# Plan-type churn
plan = pd.read_sql_query("""
    SELECT plan_type, COUNT(*) AS total_users, SUM(is_active_now) AS still_active,
           COUNT(*)-SUM(is_active_now) AS churned,
           ROUND(100.0*(COUNT(*)-SUM(is_active_now))/COUNT(*),1) AS churn_rate_pct
    FROM subs_view GROUP BY plan_type
""", conn)

# City churn
city = pd.read_sql_query("""
    SELECT city, COUNT(*) AS total_users,
           ROUND(100.0*(COUNT(*)-SUM(is_active_now))/COUNT(*),1) AS churn_rate_pct
    FROM subs_view WHERE city != 'Unknown' GROUP BY city ORDER BY churn_rate_pct DESC
""", conn)

# Average retention curve (month 0-12)
avg_curve = pd.read_sql_query(f"""
    WITH RECURSIVE month_offsets(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM month_offsets WHERE n<12),
    cus AS (
        SELECT s.user_id, m.n AS month_number,
            CASE WHEN s.churn_date IS NULL THEN 1
                 WHEN date(s.churn_date) > date(s.cohort_month,'+'||m.n||' months') THEN 1
                 ELSE 0 END AS active
        FROM subs_view s CROSS JOIN month_offsets m
        WHERE date(s.cohort_month,'+'||m.n||' months') <= '{CURRENT_DATE}'
    )
    SELECT month_number, ROUND(100.0*SUM(active)/COUNT(*),1) AS avg_retention_pct
    FROM cus GROUP BY month_number ORDER BY month_number
""", conn)

# Quarterly cohort heatmap (clean triangular version)
heatmap = pd.read_sql_query(f"""
    WITH RECURSIVE month_offsets(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM month_offsets WHERE n<12),
    quarterly AS (
        SELECT user_id, churn_date, cohort_month,
            'Q' || ((CAST(strftime('%m', cohort_month) AS INTEGER)-1)/3 + 1) || ' ' || strftime('%Y', cohort_month) AS cohort_quarter
        FROM subs_view
    ),
    quarter_last_month AS (
        SELECT cohort_quarter, MAX(cohort_month) AS last_month_in_quarter
        FROM quarterly GROUP BY cohort_quarter
    ),
    cus AS (
        SELECT q.cohort_quarter, q.user_id, m.n AS month_number,
            CASE WHEN q.churn_date IS NULL THEN 1
                 WHEN date(q.churn_date) > date(q.cohort_month,'+'||m.n||' months') THEN 1
                 ELSE 0 END AS active
        FROM quarterly q
        JOIN quarter_last_month qlm ON qlm.cohort_quarter = q.cohort_quarter
        CROSS JOIN month_offsets m
        WHERE date(qlm.last_month_in_quarter,'+'||m.n||' months') <= '{CURRENT_DATE}'
    ),
    sizes AS (SELECT cohort_quarter, COUNT(DISTINCT user_id) AS cohort_size FROM quarterly GROUP BY cohort_quarter)
    SELECT c.cohort_quarter, s.cohort_size, c.month_number,
           ROUND(100.0*SUM(c.active)/s.cohort_size,1) AS retention_pct
    FROM cus c JOIN sizes s ON c.cohort_quarter = s.cohort_quarter
    GROUP BY c.cohort_quarter, c.month_number
""", conn)

plan.to_csv(f"{OUT_DIR}/plan_churn.csv", index=False)
city.to_csv(f"{OUT_DIR}/city_churn.csv", index=False)
avg_curve.to_csv(f"{OUT_DIR}/retention_curve.csv", index=False)
heatmap.to_csv(f"{OUT_DIR}/cohort_heatmap.csv", index=False)

print("Summaries written to output/:")
print(plan)
print()
print(avg_curve)

conn.close()
