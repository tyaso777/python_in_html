#!/usr/bin/env python3
"""Fetch license hints for Pyodide packages.

By default this script reads the official Pyodide packages page, merges any
manual review fields from the local TSV review file, queries PyPI's JSON API
for each pinned package version, and writes a review TSV with license-related
columns:

- LicenseSource
- LicenseValue
- LicenseConfidence
- LicenseDetail
- LicenseURL

The script can also read a local TSV directly with `--source tsv`.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


DEFAULT_PYODIDE_PACKAGES_URL = "https://pyodide.org/en/stable/usage/packages-in-pyodide.html"
DEFAULT_INPUT = Path("docs/package_reviews/pyodide_package_review.tsv")
DEFAULT_OUTPUT = Path("docs/package_reviews/pyodide_package_review_with_licenses.tsv")
BASE_REVIEW_FIELDS = ["Name", "Version", "Status", "Description", "Decision"]


class PackageTableParser(HTMLParser):
    """Extract the Name / Version table from the Pyodide package page."""

    def __init__(self) -> None:
        super().__init__()
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._cell_tag = ""
        self._current_cell: list[str] = []
        self._current_row: list[str] = []
        self._current_headers: list[str] = []
        self._rows: list[list[str]] = []
        self.tables: list[tuple[list[str], list[list[str]]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
            self._current_headers = []
            self._rows = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"th", "td"}:
            self._in_cell = True
            self._cell_tag = tag
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._in_row and self._in_cell and tag == self._cell_tag:
            value = " ".join("".join(self._current_cell).split())
            if self._cell_tag == "th":
                self._current_headers.append(value)
            elif value:
                self._current_row.append(value)
            self._in_cell = False
            self._cell_tag = ""
            self._current_cell = []
            return

        if self._in_table and self._in_row and tag == "tr":
            if self._current_row:
                self._rows.append(self._current_row)
            self._in_row = False
            self._current_row = []
            return

        if self._in_table and tag == "table":
            self.tables.append((self._current_headers[:], self._rows[:]))
            self._in_table = False
            self._current_headers = []
            self._rows = []


def fetch_text(url: str, timeout: float) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "python-in-html-license-audit/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fetch_pyodide_package_rows(url: str, timeout: float) -> list[dict[str, str]]:
    parser = PackageTableParser()
    parser.feed(fetch_text(url, timeout))

    for headers, rows in parser.tables:
        normalized_headers = [header.strip() for header in headers]
        if normalized_headers[:2] != ["Name", "Version"]:
            continue
        return [
            {"Name": row[0].strip(), "Version": row[1].strip()}
            for row in rows
            if len(row) >= 2 and row[0].strip() and row[1].strip()
        ]

    raise ValueError(f"Could not find a Name/Version package table in {url}")


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


def merge_manual_review_columns(
    package_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_exact_key = {
        (row.get("Name", "").strip(), row.get("Version", "").strip()): row
        for row in review_rows
    }
    by_name = {
        row.get("Name", "").strip(): row
        for row in review_rows
        if row.get("Name", "").strip()
    }

    merged_rows: list[dict[str, str]] = []
    for row in package_rows:
        name = row["Name"].strip()
        version = row["Version"].strip()
        review_row = by_exact_key.get((name, version)) or by_name.get(name, {})
        merged = {"Name": name, "Version": version}
        for field in BASE_REVIEW_FIELDS[2:]:
            merged[field] = review_row.get(field, "")
        merged_rows.append(merged)
    return merged_rows


def write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["pyodide", "tsv"],
        default="pyodide",
        help="Package source: the official Pyodide packages page or a local TSV (default: pyodide)",
    )
    parser.add_argument(
        "--pyodide-url",
        default=DEFAULT_PYODIDE_PACKAGES_URL,
        help=f"Official Pyodide packages page (default: {DEFAULT_PYODIDE_PACKAGES_URL})",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input TSV path or manual review TSV path (default: {DEFAULT_INPUT})",
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
        help="Overwrite the input TSV instead of writing a new file when --source=tsv",
    )
    parser.add_argument(
        "--write-base-review",
        action="store_true",
        help="Refresh the base review TSV from the official Pyodide package page before writing the license TSV",
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
    output_path: Path = input_path if args.source == "tsv" and args.in_place else args.output

    if args.source == "pyodide":
        package_rows = fetch_pyodide_package_rows(args.pyodide_url, args.timeout)
        review_rows: list[dict[str, str]] = []
        if input_path.exists():
            review_rows, _ = read_tsv(input_path)
        rows = merge_manual_review_columns(package_rows, review_rows)
        fieldnames = BASE_REVIEW_FIELDS[:]
        if args.write_base_review:
            write_tsv(input_path, rows, fieldnames)
    else:
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
