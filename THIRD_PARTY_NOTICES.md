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

## Allowlisted Pyodide Packages

The app currently allowlists 90 Pyodide built-in packages in the package picker.
The exact package/version set is derived from the official Pyodide packages page and
reviewed locally in:

- `docs/package_reviews/pyodide_package_review.tsv`
- `docs/package_reviews/pyodide_package_review_with_licenses.tsv`

Current allowlisted package names:

```text
affine, altair, apsw, astropy, attrs, autograd, beautifulsoup4, biopython,
bleach, bokeh, boost-histogram, Bottleneck, cachetools, Cartopy, cftime,
charset-normalizer, clarabel, click, cloudpickle, colorspacious, contourpy,
coolprop, crc32c, css-inline, cssselect, cvxpy-base, cycler, decorator,
docutils, fastparquet, fiona, fonttools, fsspec, galpy, geopandas, gmpy2,
google-crc32c, h3, h5py, healpy, highspy, html5lib, idna, igraph, imageio,
Jinja2, joblib, jsonpatch, jsonpointer, jsonschema, jsonschema_specifications,
kiwisolver, lazy_loader, libcst, lightgbm, logbook, lxml, lz4, MarkupSafe,
matplotlib, msgpack, networkx, nltk, numpy, opencv-python, orjson, pandas,
Pillow, pyarrow, PyMuPDF, pyproj, python-calamine, pyyaml, rasterio, regex,
ruamel.yaml, scikit-image, scikit-learn, scipy, shapely, simplejson,
sqlalchemy, statsmodels, sympy, toolz, tqdm, ujson, wordcloud, xarray, xgboost
```

These packages keep their upstream licenses. License metadata for the current
allowlist is tracked in `docs/package_reviews/pyodide_package_review_with_licenses.tsv`.

As of the current review snapshot, most included packages are backed by `medium`
or `high` confidence license metadata, while a smaller set still needs closer
manual review because the metadata is `low` or `unknown`, or because the detected
license family is more restrictive or unusual.

Packages that currently merit closer manual review include:

- `apsw`
- `biopython`
- `crc32c`
- `docutils`
- `gmpy2`
- `google-crc32c`
- `healpy`
- `igraph`
- `PyMuPDF`
- `ujson`

Official Pyodide package list:

- https://pyodide.org/en/stable/usage/packages-in-pyodide.html

## Notes

- This file is informational and not a substitute for full legal review.
- If you redistribute a bundled/offline copy of this app, keep the relevant upstream
  license texts and notices required by those dependencies.
