-- ============================================================
-- 01_data_cleaning.sql
-- Purpose: Clean raw subscription records
-- Issues handled: duplicate user_ids, missing city values
-- ============================================================

-- Step 1: Remove duplicate user_id rows — keep first occurrence
DROP TABLE IF EXISTS subs_dedup;
CREATE TABLE subs_dedup AS
SELECT *
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY user_id) AS rn
    FROM subscriptions_raw
)
WHERE rn = 1;

-- Step 2: Handle missing city — label explicitly rather than drop
-- (dropping would lose valid churn/plan data for that user)
DROP TABLE IF EXISTS subs_clean;
CREATE TABLE subs_clean AS
SELECT
    user_id,
    signup_date,
    plan_type,
    monthly_price,
    COALESCE(city, 'Unknown') AS city,
    churn_date
FROM subs_dedup;

-- Step 3: Sanity check
SELECT 'subscriptions_raw' AS stage, COUNT(*) AS row_count FROM subscriptions_raw
UNION ALL
SELECT 'subs_dedup', COUNT(*) FROM subs_dedup
UNION ALL
SELECT 'subs_clean', COUNT(*) FROM subs_clean;
