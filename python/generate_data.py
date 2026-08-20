"""
Generates a realistic subscription-user dataset for cohort retention analysis —
modeled on an Indian edtech/OTT-style subscription app, Jan 2024 signup cohorts
through Aug 2026 (current month).

Methodology: Synthetically generated (not pulled from a live production database),
but the churn behavior is grounded in real, publicly reported 2026 subscription
benchmarks (Recurly / ChurnTools): B2C subscription apps average 5-8% monthly
churn, with early "onboarding" months churning faster than later, stabilized
months — a well-documented SaaS/subscription pattern. Annual-plan subscribers
churn far less often per month than monthly-plan subscribers, which is also a
standard, well-documented industry pattern.

Run from repo root: python python/generate_data.py
"""
import pandas as pd
import numpy as np
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os

random.seed(11)
np.random.seed(11)

CURRENT_MONTH = datetime(2026, 8, 1)  # "today" for churn observation purposes
FIRST_COHORT = datetime(2024, 1, 1)

cities = ["Mumbai", "Delhi", "Bengaluru", "Patna", "Hyderabad", "Pune",
          "Chennai", "Kolkata", "Ahmedabad", "Jaipur"]

# Monthly churn hazard by (plan_type, tenure_bucket) — grounded in real B2C
# subscription benchmarks: higher early churn, stabilizing over time; annual
# plans churn far less per month than monthly plans.
def monthly_churn_prob(plan_type, tenure_month):
    if plan_type == "Monthly":
        if tenure_month <= 1: return 0.13   # first month: high "trial-like" drop-off
        if tenure_month <= 3: return 0.09
        return 0.06
    else:  # Annual
        if tenure_month <= 1: return 0.035
        if tenure_month <= 3: return 0.02
        return 0.012

def month_range(start, end):
    months = []
    cur = start
    while cur <= end:
        months.append(cur)
        cur += relativedelta(months=1)
    return months

cohort_months = month_range(FIRST_COHORT, CURRENT_MONTH)

records = []
user_id = 1
# Business growth: more signups per month over time
for i, cohort_month in enumerate(cohort_months):
    base_signups = 220 + int(i * 14)  # growing user base over time
    n_signups = int(np.random.normal(base_signups, base_signups * 0.1))

    for _ in range(max(0, n_signups)):
        plan_type = random.choices(["Monthly", "Annual"], weights=[70, 30])[0]
        city = random.choice(cities)
        price = 299 if plan_type == "Monthly" else 2499

        # Simulate month-by-month survival until churn or CURRENT_MONTH
        churn_date = None
        months_since_signup = 0
        max_months = (CURRENT_MONTH.year - cohort_month.year) * 12 + (CURRENT_MONTH.month - cohort_month.month)

        for m in range(max_months + 1):
            if m == 0:
                continue  # signup month itself, always "active"
            p_churn = monthly_churn_prob(plan_type, m)
            if random.random() < p_churn:
                churn_date = cohort_month + relativedelta(months=m)
                break

        records.append({
            "user_id": user_id,
            "signup_date": cohort_month.strftime("%Y-%m-%d"),
            "plan_type": plan_type,
            "monthly_price": price,
            "city": city,
            "churn_date": churn_date.strftime("%Y-%m-%d") if churn_date else None,
        })
        user_id += 1

df = pd.DataFrame(records)

# Inject real-world messiness: a few duplicate rows and some missing city values
dupes = df.sample(30, random_state=2)
df = pd.concat([df, dupes], ignore_index=True)
missing_idx = df.sample(frac=0.015, random_state=4).index
df.loc[missing_idx, "city"] = None

os.makedirs("data", exist_ok=True)
df.to_csv("data/subscriptions.csv", index=False)

print("Total signup records:", df.shape)
print("Still-active users:", df["churn_date"].isna().sum())
print("Churned users:", df["churn_date"].notna().sum())
print("Overall churn rate: {:.1f}%".format(100 * df["churn_date"].notna().sum() / len(df)))
print("\nBy plan type:")
print(df.groupby("plan_type")["churn_date"].apply(lambda s: f"{100*s.notna().sum()/len(s):.1f}% churned"))
