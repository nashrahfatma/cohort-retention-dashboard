-- ============================================================
-- 02_cohort_analysis.sql
-- Purpose: Cohort retention analysis — the core "so what" of this project
-- Techniques: CTEs, recursive CTE (month series), window functions, self-referencing logic
-- ============================================================

-- Convenience view: signup cohort month + churn month (NULL = still active)
DROP VIEW IF EXISTS subs_view;
CREATE VIEW subs_view AS
SELECT
    user_id,
    plan_type,
    city,
    monthly_price,
    date(signup_date, 'start of month') AS cohort_month,
    signup_date,
    churn_date,
    CASE WHEN churn_date IS NULL THEN 1 ELSE 0 END AS is_active_now
FROM subs_clean;


-- Q1: Overall churn rate by plan type
SELECT
    plan_type,
    COUNT(*) AS total_users,
    SUM(is_active_now) AS still_active,
    COUNT(*) - SUM(is_active_now) AS churned,
    ROUND(100.0 * (COUNT(*) - SUM(is_active_now)) / COUNT(*), 1) AS churn_rate_pct
FROM subs_view
GROUP BY plan_type;


-- Q2: COHORT RETENTION TABLE — % of each signup cohort still active N months later
-- Uses a recursive CTE to generate month offsets 0-20, then checks whether each
-- user was still active at (cohort_month + N months).
WITH RECURSIVE month_offsets(n) AS (
    SELECT 0
    UNION ALL
    SELECT n + 1 FROM month_offsets WHERE n < 20
),
cohort_user_status AS (
    SELECT
        s.cohort_month,
        s.user_id,
        m.n AS month_number,
        CASE
            WHEN s.churn_date IS NULL THEN 1
            WHEN date(s.churn_date) > date(s.cohort_month, '+' || m.n || ' months') THEN 1
            ELSE 0
        END AS active_at_month_n
    FROM subs_view s
    CROSS JOIN month_offsets m
    -- only count month offsets that have actually occurred by Aug 2026
    WHERE date(s.cohort_month, '+' || m.n || ' months') <= '2026-08-01'
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
    FROM subs_view GROUP BY cohort_month
)
SELECT
    c.cohort_month,
    cs.cohort_size,
    c.month_number,
    ROUND(100.0 * SUM(c.active_at_month_n) / cs.cohort_size, 1) AS retention_pct
FROM cohort_user_status c
JOIN cohort_sizes cs ON c.cohort_month = cs.cohort_month
GROUP BY c.cohort_month, c.month_number
ORDER BY c.cohort_month, c.month_number;


-- Q3: Average retention curve across ALL cohorts (month 0 to 12) — window function: AVG
WITH RECURSIVE month_offsets(n) AS (
    SELECT 0 UNION ALL SELECT n + 1 FROM month_offsets WHERE n < 12
),
cohort_user_status AS (
    SELECT
        s.cohort_month, s.user_id, s.plan_type, m.n AS month_number,
        CASE
            WHEN s.churn_date IS NULL THEN 1
            WHEN date(s.churn_date) > date(s.cohort_month, '+' || m.n || ' months') THEN 1
            ELSE 0
        END AS active_at_month_n
    FROM subs_view s
    CROSS JOIN month_offsets m
    WHERE date(s.cohort_month, '+' || m.n || ' months') <= '2026-08-01'
)
SELECT
    month_number,
    ROUND(100.0 * SUM(active_at_month_n) / COUNT(*), 1) AS avg_retention_pct
FROM cohort_user_status
GROUP BY month_number
ORDER BY month_number;


-- Q4: City-wise churn rate (business/regional signal)
SELECT
    city,
    COUNT(*) AS total_users,
    ROUND(100.0 * (COUNT(*) - SUM(is_active_now)) / COUNT(*), 1) AS churn_rate_pct
FROM subs_view
WHERE city != 'Unknown'
GROUP BY city
ORDER BY churn_rate_pct DESC;


-- Q5: Monthly revenue retained vs lost to churn (business impact in ₹)
SELECT
    strftime('%Y-%m', churn_date) AS churn_month,
    COUNT(*) AS users_churned,
    SUM(monthly_price) AS monthly_revenue_lost
FROM subs_view
WHERE churn_date IS NOT NULL
GROUP BY churn_month
ORDER BY churn_month;
