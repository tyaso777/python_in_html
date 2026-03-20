# %%
# Input files:
# - /inputs/load_test_users.csv
# - /inputs/load_test_purchases.csv

import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def elapsed(start):
    return round(time.perf_counter() - start, 3)


print("inputs =", os.listdir("/inputs"))

# %%
t0 = time.perf_counter()
users = pd.read_csv("/inputs/load_test_users.csv")
purchases = pd.read_csv("/inputs/load_test_purchases.csv")

print("load seconds =", elapsed(t0))
print("users rows    =", len(users))
print("purchases rows=", len(purchases))
print("users cols    =", list(users.columns))
print("purchases cols=", list(purchases.columns))

# %%
t0 = time.perf_counter()
df = purchases.merge(users, on="user_id", how="left")
df["net_amount"] = df["amount"] * df["quantity"] * (1 - df["discount_rate"])
df["purchase_date"] = pd.to_datetime(df["purchase_at"]).dt.date.astype(str)

print("merge seconds =", elapsed(t0))
print("merged rows   =", len(df))
print(df.head())

# %%
t0 = time.perf_counter()
region_category = (
    df.groupby(["region", "category"], as_index=False)
      .agg(
          orders=("purchase_id", "count"),
          units=("quantity", "sum"),
          revenue=("net_amount", "sum"),
          avg_score=("score", "mean"),
      )
      .sort_values(["revenue", "orders"], ascending=[False, False])
)

top_users = (
    df.groupby(["user_id", "user_name", "region"], as_index=False)["net_amount"]
      .sum()
      .sort_values("net_amount", ascending=False)
      .head(100)
)

pivot = pd.pivot_table(
    df,
    index="purchase_date",
    columns="region",
    values="net_amount",
    aggfunc="sum",
    fill_value=0.0,
).sort_index()

print("aggregate seconds =", elapsed(t0))
print(region_category.head(10))
print(top_users.head(10))
print(pivot.tail())

# %%
t0 = time.perf_counter()
region_summary = (
    df.groupby("region", as_index=False)["net_amount"]
      .sum()
      .sort_values("net_amount", ascending=False)
)

fig, axes = plt.subplots(2, 1, figsize=(10, 8))
axes[0].bar(region_summary["region"], region_summary["net_amount"], color="#1f77b4")
axes[0].set_title("Net Revenue by Region")
axes[0].tick_params(axis="x", rotation=20)

top_plot = top_users.head(20).sort_values("net_amount", ascending=True)
axes[1].barh(top_plot["user_name"], top_plot["net_amount"], color="#2ca02c")
axes[1].set_title("Top 20 Users by Net Revenue")

plt.tight_layout()
plt.savefig("/outputs/load_test_summary.png", dpi=140)
plt.close(fig)

region_category.to_csv("/outputs/load_test_region_category.csv", index=False)
top_users.to_csv("/outputs/load_test_top_users.csv", index=False)
pivot.to_csv("/outputs/load_test_daily_region_pivot.csv")

print("output seconds =", elapsed(t0))
print("saved:")
print(" - /outputs/load_test_summary.png")
print(" - /outputs/load_test_region_category.csv")
print(" - /outputs/load_test_top_users.csv")
print(" - /outputs/load_test_daily_region_pivot.csv")

# %%
t0 = time.perf_counter()
rolling = (
    pivot.rolling(window=7, min_periods=1)
         .mean()
         .tail(20)
)

print("rolling seconds =", elapsed(t0))
print(rolling)
