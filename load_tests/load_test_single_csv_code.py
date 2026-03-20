# %%
# Input files:
# - One of these files:
#   /inputs/load_test_single_xxlarge.csv
#   /inputs/load_test_single_xlarge.csv
#   /inputs/load_test_single_large_profile.csv
#   /inputs/load_test_single_medium.csv
#   /inputs/load_test_single_large.csv

import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def elapsed(start):
    return round(time.perf_counter() - start, 3)


available_inputs = set(os.listdir("/inputs"))
single_csv_candidates = [
    "load_test_single_xxlarge.csv",
    "load_test_single_xlarge.csv",
    "load_test_single_large_profile.csv",
    "load_test_single_medium.csv",
    "load_test_single_large.csv",
]

selected_single_csv = next(
    (name for name in single_csv_candidates if name in available_inputs),
    None,
)

if selected_single_csv is None:
    raise FileNotFoundError(
        "No single CSV load test input was found in /inputs. "
        f"Expected one of: {', '.join(single_csv_candidates)}"
    )

selected_input_path = f"/inputs/{selected_single_csv}"

print("inputs =", sorted(available_inputs))
print("selected_input_path =", selected_input_path)

# %%
t0 = time.perf_counter()
df = pd.read_csv(selected_input_path)
print("read seconds =", elapsed(t0))
print("rows         =", len(df))
print("columns      =", list(df.columns))
print(df.head())

# %%
t0 = time.perf_counter()
df["event_date"] = pd.to_datetime(df["event_date"])
df["is_hot"] = df["flag_hot"] == "Y"
df["is_new"] = df["flag_new"] == "Y"
df["weighted_value"] = df["metric_a"] * df["ratio"] + df["metric_b"]

daily = (
    df.groupby(["event_date", "region"], as_index=False)
      .agg(
          rows=("row_id", "count"),
          hot_rows=("is_hot", "sum"),
          new_rows=("is_new", "sum"),
          weighted_value=("weighted_value", "sum"),
          avg_score=("score", "mean"),
      )
      .sort_values(["event_date", "region"])
)

segment_summary = (
    df.groupby(["segment", "channel", "status"], as_index=False)
      .agg(
          rows=("row_id", "count"),
          metric_a=("metric_a", "sum"),
          metric_b=("metric_b", "sum"),
          avg_ratio=("ratio", "mean"),
      )
      .sort_values("metric_b", ascending=False)
)

print("transform seconds =", elapsed(t0))
print(daily.head())
print(segment_summary.head())

# %%
t0 = time.perf_counter()
top_regions = (
    df.groupby("region", as_index=False)["weighted_value"]
      .sum()
      .sort_values("weighted_value", ascending=False)
)

fig, axes = plt.subplots(2, 1, figsize=(10, 8))
axes[0].bar(top_regions["region"], top_regions["weighted_value"], color="#3366cc")
axes[0].set_title("Weighted Value by Region")
axes[0].tick_params(axis="x", rotation=20)

top_segments = segment_summary.head(15).sort_values("metric_b", ascending=True)
axes[1].barh(
    top_segments["segment"] + " | " + top_segments["channel"],
    top_segments["metric_b"],
    color="#dc3912",
)
axes[1].set_title("Top Segment / Channel by metric_b")

plt.tight_layout()
plt.savefig("/outputs/load_test_single_summary.png", dpi=140)
plt.close(fig)

daily.to_csv("/outputs/load_test_single_daily.csv", index=False)
segment_summary.to_csv("/outputs/load_test_single_segments.csv", index=False)

print("output seconds =", elapsed(t0))
print("saved:")
print(" - /outputs/load_test_single_summary.png")
print(" - /outputs/load_test_single_daily.csv")
print(" - /outputs/load_test_single_segments.csv")

# %%
t0 = time.perf_counter()
filtered = df.loc[
    (df["metric_a"] >= 2500)
    & (df["metric_b"] >= 500.0)
    & (df["status"].isin(["active", "won"]))
]

wide = pd.pivot_table(
    filtered,
    index="region",
    columns="segment",
    values="weighted_value",
    aggfunc="mean",
    fill_value=0.0,
)

print("filter/pivot seconds =", elapsed(t0))
print(filtered.head())
print(wide)
