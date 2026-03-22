# Python in HTML

Single-file browser Python notebook powered by Pyodide.

## Overview

Python in HTML runs Python directly in the browser and keeps the app in one HTML file.
It supports cell-based execution, input files, per-operation result history, image previews,
downloadable outputs, package selection, and config save/load.

## Main Features

- Run Python in the browser with Pyodide
- Edit code with a CodeMirror-based cell editor
- Load files into `/inputs/`
- Save generated files to `/outputs/`
- Preview images and download generated files from the UI
- Use `# %%` cells, `Shift + Enter`, and `Ctrl + Enter`
- Save, load, and restore app config
- Read Excel files through the app compatibility adapter for `pd.read_excel(...)`

## Main Files

- `python_in_html.html`: the main app
- `docs/guide.html`: detailed in-app user guide
- `samples/`: small sample CSV files for quick local testing
- `tests/test_excel_read_adapter.py`: Excel compatibility tests
- `load_tests/`: load-test scripts, configs, and generators

## Quick Start

1. Open `python_in_html.html` in a browser.
2. Choose input files in the `Input files` panel.
3. Edit Python code.
4. Run a cell or all cells.
5. Check `Operation Results`.

## Documentation

- In-app guide: `docs/guide.html`

The repository also includes a folder-import demo in:

- `samples/folder_input_demo/`
- `samples/folder_input_demo_config.json`

See `docs/guide.html` for the recommended flow.

## Package Review Files

- `docs/package_reviews/pyodide_package_review.tsv`: review table based on the official Pyodide packages page, with local review columns such as `Status`, `Description`, and `Decision`
- `docs/package_reviews/pyodide_package_review_with_licenses.tsv`: the same review table with fetched license metadata
- `scripts/fetch_package_licenses.py`: helper script that reads the official Pyodide packages page, merges local review fields, and appends license-related columns

The package source page is:

- `https://pyodide.org/en/stable/usage/packages-in-pyodide.html`

## License Metadata Flow

`scripts/fetch_package_licenses.py` does not treat
`docs/package_reviews/pyodide_package_review.tsv` as the package source of truth.
The source of truth for the package list is the official Pyodide packages page, and
the local TSV is used to keep this project's manual review fields.

The package review flow is:

1. Read the package list from the official Pyodide packages page
2. Match each package by `Name` / `Version`
3. Merge local review fields from `docs/package_reviews/pyodide_package_review.tsv`, such as `Status`, `Description`, and `Decision`
4. Query PyPI release metadata for each `Name` / `Version`
5. Write the result to `docs/package_reviews/pyodide_package_review_with_licenses.tsv`
6. Use that result to support UI-facing license classification such as `Generally OK` and `Review Needed`

Example:

```bash
python scripts/fetch_package_licenses.py
```

By default, the script reads:

- `https://pyodide.org/en/stable/usage/packages-in-pyodide.html`
- `docs/package_reviews/pyodide_package_review.tsv`

and writes:

- `docs/package_reviews/pyodide_package_review_with_licenses.tsv`

If you also want to refresh the base review TSV from the official page before writing the license TSV:

```bash
python scripts/fetch_package_licenses.py --write-base-review
```

That mode is useful when the official Pyodide page changes and you want to pull the
latest `Name` / `Version` list into the local review TSV before continuing manual review.

The script checks PyPI release metadata for each `Name` / `Version` pair and appends:

- `LicenseSource`
- `LicenseValue`
- `LicenseConfidence`
- `LicenseDetail`
- `LicenseURL`

## License Confidence

`LicenseConfidence` is a rule-based label derived from which metadata field produced the result.
It is not a probability score.

- `high`: taken from `license_expression`
- `medium`: taken from `classifiers` such as `License :: ...`
- `low`: taken from the free-text `license` field
- `unknown`: no usable license field was found, or metadata fetch failed

In practice, `unknown` and `low` entries should be reviewed first.

## License Review

The app also uses a simpler UI-facing classification:

- `Generally OK`
- `Review Needed`

This is a conservative screening rule for internal package selection, not legal advice.

`Generally OK` is used when the normalized license result only contains licenses that are treated as generally acceptable in this project, such as:

- `MIT`
- `BSD`
- `Apache-2.0`
- `PSF`
- `MPL-2.0`
- `AFL`
- `BSL-1.0`

`Review Needed` is used when any detected license falls into a manual-review bucket, such as:

- `Unknown`
- `GPL`
- `LGPL`
- `AGPL-3.0-or-Commercial`
- `Freely Distributable`
- `Public Domain`
- `any-OSI`

If a package has multiple detected licenses, one manual-review license is enough to classify the package as `Review Needed`.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

This project also uses third-party libraries, including Pyodide, CodeMirror, and SheetJS, which are distributed under their own licenses.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for a practical summary.
