from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


REGIONS = ["APAC", "EMEA", "Japan", "LATAM", "North America"]
SEGMENTS = ["consumer", "enterprise", "public", "smb"]
CATEGORIES = [
    "analytics",
    "compute",
    "database",
    "network",
    "observability",
    "storage",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate CSV inputs for Python in HTML load testing.")
    parser.add_argument("--users", type=int, default=20_000, help="Number of users to generate.")
    parser.add_argument("--purchases", type=int, default=250_000, help="Number of purchases to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("."),
        help="Directory where CSV files will be written.",
    )
    return parser


def iso_day(base: datetime, offset_days: int) -> str:
    return (base + timedelta(days=offset_days)).strftime("%Y-%m-%d")


def iso_timestamp(base: datetime, offset_minutes: int) -> str:
    return (base + timedelta(minutes=offset_minutes)).strftime("%Y-%m-%d %H:%M:%S")


def write_users_csv(path: Path, user_count: int, rng: random.Random) -> None:
    signup_base = datetime(2022, 1, 1)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "user_name", "region", "segment", "signup_date", "score"])
        for user_id in range(1, user_count + 1):
            writer.writerow([
                user_id,
                f"user_{user_id:05d}",
                rng.choice(REGIONS),
                rng.choice(SEGMENTS),
                iso_day(signup_base, rng.randint(0, 365 * 3)),
                round(rng.uniform(0.0, 100.0), 3),
            ])


def write_purchases_csv(path: Path, purchase_count: int, user_count: int, rng: random.Random) -> None:
    purchase_base = datetime(2024, 1, 1, 9, 0, 0)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "purchase_id",
            "user_id",
            "category",
            "amount",
            "quantity",
            "discount_rate",
            "purchase_at",
        ])
        for purchase_id in range(1, purchase_count + 1):
            writer.writerow([
                purchase_id,
                rng.randint(1, user_count),
                rng.choice(CATEGORIES),
                round(rng.uniform(10.0, 3000.0), 2),
                rng.randint(1, 8),
                round(rng.uniform(0.0, 0.35), 3),
                iso_timestamp(purchase_base, rng.randint(0, 60 * 24 * 500)),
            ])


def main() -> None:
    args = build_parser().parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    users_path = args.outdir / "load_test_users.csv"
    purchases_path = args.outdir / "load_test_purchases.csv"

    write_users_csv(users_path, args.users, rng)
    write_purchases_csv(purchases_path, args.purchases, args.users, rng)

    print(f"Wrote {users_path}")
    print(f"Wrote {purchases_path}")
    print(f"users={args.users} purchases={args.purchases} seed={args.seed}")


if __name__ == "__main__":
    main()
