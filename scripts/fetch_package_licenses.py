#!/usr/bin/env python3
"""Fetch license hints for packages listed in a TSV review file.

This script reads a TSV with at least `Name` and `Version` columns, queries
PyPI's JSON API for each pinned package version, and appends license-related
columns:

- LicenseSource
- LicenseValue
- LicenseConfidence
- LicenseDetail
- LicenseURL

The result is written to a new TSV by default so the source review file stays
unchanged unless `--in-place` is explicitly used.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_INPUT = Path("pyodide_package_review.tsv")
DEFAULT_OUTPUT = Path("pyodide_package_review_with_licenses.tsv")


def fetch_release_json(name: str, version: str, timeout: float) -> dict:
    quoted_name = urllib.parse.quote(name, safe="")
    quoted_version = urllib.parse.quote(version, safe="")
    url = f"https://pypi.org/pypi/{quoted_name}/{quoted_version}/json"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "python-in-html-license-audit/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def extract_license_info(payload: dict) -> tuple[str, str, str, str]:
    info = payload.get("info", {})

    license_expression = info.get("license_expression")
    if license_expression:
        return (
            "PyPI JSON: license_expression",
            str(license_expression),
            "high",
            "Exact SPDX-style expression from PyPI metadata",
        )

    classifiers = [
        item
        for item in info.get("classifiers", [])
        if isinstance(item, str) and item.startswith("License ::")
    ]
    if classifiers:
        return (
            "PyPI JSON: classifiers",
            " | ".join(classifiers),
            "medium",
            "License classifiers declared in package metadata",
        )

    license_text = info.get("license")
    if isinstance(license_text, str) and license_text.strip():
        return (
            "PyPI JSON: license",
            license_text.strip().replace("\n", " "),
            "low",
            "Free-text license field from package metadata",
        )

    return (
        "PyPI JSON: missing",
        "",
        "unknown",
        "No usable license field was present in the release metadata",
    )


def append_license_columns(rows: list[dict[str, str]], timeout: float) -> list[dict[str, str]]:
    for row in rows:
        name = row.get("Name", "").strip()
        version = row.get("Version", "").strip()
        license_url = ""

        if not name or not version:
            row["LicenseSource"] = "input: missing"
            row["LicenseValue"] = ""
            row["LicenseConfidence"] = "unknown"
            row["LicenseDetail"] = "Missing Name or Version in TSV row"
            row["LicenseURL"] = ""
            continue

        license_url = f"https://pypi.org/project/{name}/{version}/"

        try:
            payload = fetch_release_json(name, version, timeout)
            source, value, confidence, detail = extract_license_info(payload)
        except urllib.error.HTTPError as exc:
            source = "PyPI JSON: error"
            value = ""
            confidence = "unknown"
            detail = f"HTTP {exc.code} while fetching release metadata"
        except urllib.error.URLError as exc:
            source = "PyPI JSON: error"
            value = ""
            confidence = "unknown"
            detail = f"Network error: {exc.reason}"
        except TimeoutError:
            source = "PyPI JSON: error"
            value = ""
            confidence = "unknown"
            detail = "Request timed out"
        except Exception as exc:  # pragma: no cover - defensive catch
            source = "PyPI JSON: error"
            value = ""
            confidence = "unknown"
            detail = f"Unexpected error: {type(exc).__name__}: {exc}"

        row["LicenseSource"] = source
        row["LicenseValue"] = value
        row["LicenseConfidence"] = confidence
        row["LicenseDetail"] = detail
        row["LicenseURL"] = license_url

    return rows


def read_tsv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"No header row found in {path}")
        rows = list(reader)
        return rows, list(reader.fieldnames)


def write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input TSV path (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output TSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input TSV instead of writing a new file",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds (default: 20)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path: Path = args.input
    output_path: Path = input_path if args.in_place else args.output

    rows, fieldnames = read_tsv(input_path)
    extra_fields = [
        "LicenseSource",
        "LicenseValue",
        "LicenseConfidence",
        "LicenseDetail",
        "LicenseURL",
    ]
    merged_fieldnames = fieldnames + [field for field in extra_fields if field not in fieldnames]
    rows = append_license_columns(rows, args.timeout)
    write_tsv(output_path, rows, merged_fieldnames)

    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
