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

## License

This repository is licensed under the terms in `LICENSE`.
