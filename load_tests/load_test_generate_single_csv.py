from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


REGIONS = ["APAC", "EMEA", "Japan", "LATAM", "North America"]
SEGMENTS = ["consumer", "enterprise", "public", "smb"]
CHANNELS = ["ads", "affiliate", "direct", "partner", "referral", "social"]
STATUSES = ["active", "paused", "trial", "won", "lost"]

PROFILES = {
    "small": {"rows": 120_000},
    "medium": {"rows": 350_000},
    "large": {"rows": 900_000},
    "xlarge": {"rows": 2_300_000},
    "xxlarge": {"rows": 3_400_000},
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a single large CSV for Python in HTML load testing.")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="medium", help="Preset size profile.")
    parser.add_argument("--rows", type=int, default=None, help="Override row count.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    parser.add_argument(
        "--outfile",
        type=Path,
        default=Path("load_test_single_large.csv"),
        help="Output CSV path.",
    )
    return parser


def iso_day(base: datetime, offset_days: int) -> str:
    return (base + timedelta(days=offset_days)).strftime("%Y-%m-%d")


def main() -> None:
    args = build_parser().parse_args()
    rows = args.rows if args.rows is not None else PROFILES[args.profile]["rows"]
    args.outfile.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    base = datetime(2023, 1, 1)

    with args.outfile.open("w", encoding="utf-8", newline="") as f:
      writer = csv.writer(f)
      writer.writerow([
          "row_id",
          "event_date",
          "region",
          "segment",
          "channel",
          "status",
          "metric_a",
          "metric_b",
          "metric_c",
          "score",
          "ratio",
          "flag_hot",
          "flag_new",
          "text_code",
      ])

      for row_id in range(1, rows + 1):
          metric_a = rng.randint(1, 10_000)
          metric_b = round(rng.uniform(0.0, 5000.0), 3)
          metric_c = rng.randint(0, 300)
          writer.writerow([
              row_id,
              iso_day(base, rng.randint(0, 730)),
              rng.choice(REGIONS),
              rng.choice(SEGMENTS),
              rng.choice(CHANNELS),
              rng.choice(STATUSES),
              metric_a,
              metric_b,
              metric_c,
              round(rng.uniform(0.0, 100.0), 4),
              round(metric_b / max(metric_a, 1), 6),
              "Y" if metric_a > 8000 else "N",
              "Y" if rng.random() < 0.08 else "N",
              f"C{rng.randint(1000, 9999)}",
          ])

    print(f"Wrote {args.outfile}")
    print(f"rows={rows} profile={args.profile} seed={args.seed}")


if __name__ == "__main__":
    main()
