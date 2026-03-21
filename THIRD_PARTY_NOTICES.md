# Third-Party Notices

This project is distributed under the MIT License. It also depends on third-party
browser/runtime components and optional Python packages that are distributed under
their own licenses.

## Scope

This file is a practical notice for this repository.

- Core browser/runtime dependencies are listed explicitly below.
- Python packages loaded through Pyodide keep their upstream licenses.
- The package list available in the UI is an allowlist of Pyodide built-in packages,
  not an arbitrary `pip install` list.
- Before redistribution in a stricter environment, review the exact licenses of the
  Pyodide version and package set you ship.

## Core Browser and Runtime Dependencies

| Component | Role | License | Source |
| --- | --- | --- | --- |
| Pyodide | Python runtime in the browser | MPL-2.0 | https://github.com/pyodide/pyodide |
| CodeMirror 5 | Code editor UI | MIT | https://github.com/codemirror/codemirror5 |
| SheetJS Community Edition | Excel parsing in the browser | Apache-2.0 | https://docs.sheetjs.com/docs/miscellany/license/ |

## Common Pyodide Built-in Python Packages

These are representative packages used directly by the app or shown prominently in the UI.
They keep their upstream project licenses.

| Package | Typical Use Here | License | Upstream |
| --- | --- | --- | --- |
| NumPy | arrays and numerics | BSD-3-Clause | https://numpy.org/ |
| pandas | tabular data and CSV work | BSD-3-Clause | https://pandas.pydata.org/ |
| SciPy | scientific computing | BSD-3-Clause | https://scipy.org/ |
| scikit-learn | machine learning | BSD-3-Clause | https://scikit-learn.org/ |
| Matplotlib | plotting | Matplotlib license, BSD-compatible and based on the PSF license | https://matplotlib.org/stable/project/license.html |
| SymPy | symbolic math | BSD-3-Clause | https://www.sympy.org/ |
| Beautiful Soup 4 | HTML parsing | MIT | https://www.crummy.com/software/BeautifulSoup/ |
| SQLAlchemy | SQL toolkit | MIT | https://www.sqlalchemy.org/ |

## Optional Allowlisted Packages

The app also exposes many additional Pyodide built-in packages through the package picker,
including data, plotting, text, geo, image, and science packages.

Those packages are:

- Selected from Pyodide built-ins for a pinned Pyodide release
- Still governed by their own upstream licenses
- Best reviewed individually before redistribution or policy approval in sensitive environments

Official Pyodide package list:

- https://pyodide.org/en/stable/usage/packages-in-pyodide.html

## Notes

- This file is informational and not a substitute for full legal review.
- If you redistribute a bundled/offline copy of this app, keep the relevant upstream
  license texts and notices required by those dependencies.
