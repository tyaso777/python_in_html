import copy
import json
import re
import subprocess
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT_DIR = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT_DIR / "python_in_html.html"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"
GENERATE_FIXTURES_SCRIPT = ROOT_DIR / "tests" / "scripts" / "generate_excel_fixtures.py"


def extract_excel_adapter_source():
    html = HTML_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"async function ensureExcelReadAdapterInstalled\(\)\s*\{.*?await pyodide\.runPythonAsync\(`\n(.*?)`\);\n\s*\}",
        html,
        re.S,
    )
    if not match:
        raise AssertionError("Could not extract Excel adapter source from python_in_html.html")
    return match.group(1)


def parse_inline_value(cell, namespace):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        text_el = cell.find("./main:is/main:t", namespace)
        return text_el.text if text_el is not None else ""

    value_el = cell.find("./main:v", namespace)
    if value_el is None:
        return None

    raw = value_el.text
    if raw is None:
        return None
    if raw.isdigit():
        return int(raw)
    try:
        return float(raw)
    except ValueError:
        return raw


def column_index_from_ref(cell_ref):
    letters = "".join(char for char in cell_ref if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - 64)
    return index - 1


def load_fixture_workbook(path):
    namespace = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
        "docrel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    with ZipFile(path) as zf:
        workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
        rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

        rel_targets = {}
        for rel in rels_root.findall("./rel:Relationship", namespace):
            rel_targets[rel.attrib["Id"]] = rel.attrib["Target"]

        sheet_names = []
        sheets = {}
        for sheet in workbook_root.findall("./main:sheets/main:sheet", namespace):
            sheet_name = sheet.attrib["name"]
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_targets[rel_id]
            sheet_root = ET.fromstring(zf.read(f"xl/{target}"))
            rows = []
            max_width = 0
            for row in sheet_root.findall("./main:sheetData/main:row", namespace):
                values = []
                for cell in row.findall("./main:c", namespace):
                    ref = cell.attrib.get("r", "")
                    col_index = column_index_from_ref(ref)
                    while len(values) < col_index:
                        values.append(None)
                    values.append(parse_inline_value(cell, namespace))
                max_width = max(max_width, len(values))
                rows.append(values)
            rows = [row + [None] * (max_width - len(row)) for row in rows]
            sheet_names.append(sheet_name)
            sheets[sheet_name] = rows

    return {
        "sheetNames": sheet_names,
        "sheets": sheets,
    }


class FakeMultiIndex(list):
    @classmethod
    def from_arrays(cls, arrays):
        return cls(list(zip(*arrays)))


class FakeSeries(list):
    pass


class FakeILoc:
    def __init__(self, df):
        self.df = df

    def __getitem__(self, key):
        if isinstance(key, slice):
            return FakeDataFrame(copy.deepcopy(self.df.rows[key]), list(self.df.columns))
        raise NotImplementedError(f"Unsupported iloc key: {key!r}")


class FakeLoc:
    def __init__(self, df):
        self.df = df

    def __getitem__(self, key):
        rows, cols = key
        if rows != slice(None, None, None):
            raise NotImplementedError(f"Unsupported row selector: {rows!r}")
        selected = self.df.select_columns(cols)
        return selected


class FakeDataFrame:
    def __init__(self, data, columns=None):
        normalized_rows = []
        if data and isinstance(data[0], dict):
            if columns is None:
                columns = list(data[0].keys())
            for row in data:
                normalized_rows.append([row.get(col) for col in columns])
        else:
            normalized_rows = [list(row) for row in data]
            if columns is None:
                width = max((len(row) for row in normalized_rows), default=0)
                columns = list(range(width))

        self.columns = list(columns)
        self.rows = []
        for row in normalized_rows:
            padded = list(row) + [None] * max(0, len(self.columns) - len(row))
            self.rows.append(padded[: len(self.columns)])

        self.index_keys = None
        self.dtype_applied = None

    @property
    def iloc(self):
        return FakeILoc(self)

    @property
    def loc(self):
        return FakeLoc(self)

    def copy(self):
        cloned = FakeDataFrame(copy.deepcopy(self.rows), list(self.columns))
        cloned.index_keys = copy.deepcopy(self.index_keys)
        cloned.dtype_applied = copy.deepcopy(self.dtype_applied)
        return cloned

    def _column_index(self, key):
        if isinstance(key, int):
            return key
        return self.columns.index(key)

    def select_columns(self, keys):
        indexes = [self._column_index(key) for key in keys]
        rows = [[row[idx] for idx in indexes] for row in self.rows]
        columns = [self.columns[idx] for idx in indexes]
        return FakeDataFrame(rows, columns)

    def __getitem__(self, key):
        if isinstance(key, list):
            return self.select_columns(key)
        idx = self._column_index(key)
        return FakeSeries([row[idx] for row in self.rows])

    def __setitem__(self, key, values):
        if not isinstance(values, list):
            values = [values] * len(self.rows)
        if key in self.columns:
            idx = self.columns.index(key)
            for row, value in zip(self.rows, values):
                row[idx] = value
            return

        self.columns.append(key)
        for row, value in zip(self.rows, values):
            row.append(value)

    def replace(self, mapping_or_values, value=None):
        clone = self.copy()
        if isinstance(mapping_or_values, dict):
            mapping = mapping_or_values
        else:
            mapping = {item: value for item in mapping_or_values}
        for row_index, row in enumerate(clone.rows):
            clone.rows[row_index] = [mapping.get(cell, cell) for cell in row]
        return clone

    def astype(self, dtype):
        clone = self.copy()
        clone.dtype_applied = dtype
        if dtype is str:
            clone.rows = [[str(cell) for cell in row] for row in clone.rows]
        return clone

    def agg(self, func, axis=0):
        if axis != 1:
            raise NotImplementedError(f"Unsupported axis: {axis}")
        return [func(row) for row in self.rows]

    def set_index(self, keys):
        clone = self.copy()
        clone.index_keys = list(keys)
        return clone

    def to_rows(self):
        return copy.deepcopy(self.rows)


def fake_to_datetime(values, errors=None):
    if isinstance(values, list):
        return [f"dt:{value}" for value in values]
    return f"dt:{values}"


def build_fake_pandas(original_read_excel):
    pandas_module = types.ModuleType("pandas")
    pandas_module.DataFrame = FakeDataFrame
    pandas_module.MultiIndex = FakeMultiIndex
    pandas_module.NA = "<NA>"
    pandas_module.read_excel = original_read_excel
    pandas_module.to_datetime = fake_to_datetime
    return pandas_module


def build_fake_excel_adapter(workbooks):
    module = types.ModuleType("excel_adapter")

    def has_workbook(input_path):
        return str(input_path) in workbooks

    def get_sheet_names_json(input_path):
        workbook = workbooks[str(input_path)]
        return json.dumps(workbook["sheetNames"])

    def get_sheet_json(input_path, sheet_specifier):
        workbook = workbooks[str(input_path)]
        if isinstance(sheet_specifier, int):
            sheet_name = workbook["sheetNames"][sheet_specifier]
        elif sheet_specifier is None:
            sheet_name = workbook["sheetNames"][0]
        else:
            sheet_name = str(sheet_specifier)
        return json.dumps({
            "sheet_name": sheet_name,
            "rows": workbook["sheets"][sheet_name],
        })

    module.hasWorkbook = has_workbook
    module.getSheetNamesJson = get_sheet_names_json
    module.getSheetJson = get_sheet_json
    return module


class ExcelReadAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(GENERATE_FIXTURES_SCRIPT)], check=True)

    def setUp(self):
        self.adapter_source = extract_excel_adapter_source()
        self.original_modules = {}
        self.original_calls = []
        self.workbooks = {
            "/inputs/book.xlsx": {
                "sheetNames": ["Main", "Second"],
                "sheets": {
                    "Main": [
                        ["id", "name", "flag", "date", "amount"],
                        [1, "Alice", "Y", "2025-01-01", "10"],
                        [2, "Bob", "N", "2025-01-02", "20"],
                        [3, "Carol", None, "2025-01-03", "30"],
                    ],
                    "Second": [
                        ["code", "value"],
                        ["A", 100],
                        ["B", 200],
                    ],
                },
            },
            "/inputs/multi_header.xlsx": {
                "sheetNames": ["Sheet1"],
                "sheets": {
                    "Sheet1": [
                        ["group", "group", "meta"],
                        ["left", "right", "value"],
                        [1, 2, 3],
                    ],
                },
            },
            "/inputs/skiprows_cases.xlsx": {
                "sheetNames": ["SkipRows"],
                "sheets": {
                    "SkipRows": [
                        ["Report Title", None, None],
                        ["Generated", "2025-03-20", None],
                        ["id", "name", "score"],
                        [1, "Alice", 91],
                        [2, "Bob", 88],
                        [3, "Carol", 95],
                    ],
                },
            },
            "/inputs/usecols_cases.xlsx": {
                "sheetNames": ["Wide"],
                "sheets": {
                    "Wide": [
                        ["A_col", "B_col", "C_col", "D_col", "E_col"],
                        [1, 2, 3, 4, 5],
                        [10, 20, 30, 40, 50],
                    ],
                },
            },
            "/inputs/dates_and_na.xlsx": {
                "sheetNames": ["DatesNA"],
                "sheets": {
                    "DatesNA": [
                        ["event_date", "end_date", "flag", "amount"],
                        ["2025-01-01", "2025-01-03", "Y", "10"],
                        ["2025-02-01", None, "N", "missing"],
                        ["2025-03-01", "2025-03-05", None, "30"],
                    ],
                },
            },
            "/inputs/index_and_names.xlsx": {
                "sheetNames": ["Indexed"],
                "sheets": {
                    "Indexed": [
                        ["region", "store", "sales", "cost"],
                        ["East", "A", 100, 70],
                        ["East", "B", 120, 80],
                        ["West", "C", 90, 60],
                    ],
                },
            },
            "/inputs/ragged_rows.xlsx": {
                "sheetNames": ["Ragged"],
                "sheets": {
                    "Ragged": [
                        ["c1", "c2", "c3", "c4"],
                        [1, 2, None, None],
                        [3, 4, 5, None],
                        [6, None, None, None],
                    ],
                },
            },
            "/inputs/unicode_sheet_names.xlsx": {
                "sheetNames": ["集計 シート", "祝日-2025"],
                "sheets": {
                    "集計 シート": [
                        ["項目", "値"],
                        ["件数", 3],
                    ],
                    "祝日-2025": [
                        ["日付", "名称"],
                        ["2025-01-01", "元日"],
                    ],
                },
            },
            "/inputs/formula_like_cells.xlsx": {
                "sheetNames": ["FormulaLike"],
                "sheets": {
                    "FormulaLike": [
                        ["expr", "literal"],
                        ["=SUM(A1:B1)", "plain-text"],
                        ["=A2*10", "still-text"],
                    ],
                },
            },
            "/inputs/header_none_cases.xlsx": {
                "sheetNames": ["RawRows"],
                "sheets": {
                    "RawRows": [
                        ["meta", "version1", None],
                        ["alpha", "beta", "gamma"],
                        [1, 2, 3],
                    ],
                },
            },
        }

        def original_read_excel(*args, **kwargs):
            self.original_calls.append((args, kwargs))
            return "original-read-excel"

        self.fake_pandas = build_fake_pandas(original_read_excel)
        self.fake_excel_adapter = build_fake_excel_adapter(self.workbooks)

        for name, module in {
            "pandas": self.fake_pandas,
            "excel_adapter": self.fake_excel_adapter,
        }.items():
            self.original_modules[name] = sys.modules.get(name)
            sys.modules[name] = module

        self.namespace = {}
        exec(self.adapter_source, self.namespace)
        self.read_excel = self.fake_pandas.read_excel

    def tearDown(self):
        for name, module in self.original_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def test_fallback_to_original_read_excel_for_non_cached_path(self):
        result = self.read_excel("/inputs/not_cached.xlsx", sheet_name=0)
        self.assertEqual(result, "original-read-excel")
        self.assertEqual(self.original_calls, [(("/inputs/not_cached.xlsx",), {"sheet_name": 0})])

    def test_sheet_name_index_reads_expected_sheet(self):
        df = self.read_excel("/inputs/book.xlsx", sheet_name=0)
        self.assertEqual(df.columns, ["id", "name", "flag", "date", "amount"])
        self.assertEqual(df.to_rows()[0], [1, "Alice", "Y", "2025-01-01", "10"])

    def test_sheet_name_none_returns_dict(self):
        result = self.read_excel("/inputs/book.xlsx", sheet_name=None)
        self.assertEqual(set(result.keys()), {"Main", "Second"})
        self.assertEqual(result["Second"].columns, ["code", "value"])

    def test_header_none_keeps_numeric_columns(self):
        df = self.read_excel("/inputs/book.xlsx", header=None, nrows=2)
        self.assertEqual(df.columns, [0, 1, 2, 3, 4])
        self.assertEqual(df.to_rows()[0], ["id", "name", "flag", "date", "amount"])

    def test_header_multiindex_is_supported(self):
        df = self.read_excel("/inputs/multi_header.xlsx", header=[0, 1])
        self.assertEqual(df.columns, [("group", "left"), ("group", "right"), ("meta", "value")])
        self.assertEqual(df.to_rows(), [[1, 2, 3]])

    def test_names_overrides_columns(self):
        df = self.read_excel("/inputs/book.xlsx", names=["user_id", "user_name", "flag", "date", "amount"], nrows=1)
        self.assertEqual(df.columns, ["user_id", "user_name", "flag", "date", "amount"])

    def test_index_col_and_usecols_string_are_supported(self):
        df = self.read_excel("/inputs/book.xlsx", usecols="A:C", index_col=0)
        self.assertEqual(df.columns, ["id", "name", "flag"])
        self.assertEqual(df.index_keys, ["id"])
        self.assertEqual(df.to_rows()[1], [2, "Bob", "N"])

    def test_skiprows_list_and_nrows_are_supported(self):
        df = self.read_excel("/inputs/book.xlsx", skiprows=[1], nrows=2)
        self.assertEqual(df.to_rows(), [[2, "Bob", "N", "2025-01-02", "20"], [3, "Carol", None, "2025-01-03", "30"]])

    def test_skiprows_callable_is_supported(self):
        df = self.read_excel("/inputs/book.xlsx", skiprows=lambda idx: idx == 2)
        self.assertEqual(len(df.to_rows()), 2)
        self.assertEqual(df.to_rows()[0][0], 1)
        self.assertEqual(df.to_rows()[1][0], 3)

    def test_dtype_is_applied(self):
        df = self.read_excel("/inputs/book.xlsx", dtype={"amount": "float64"})
        self.assertEqual(df.dtype_applied, {"amount": "float64"})

    def test_parse_dates_list_is_supported(self):
        df = self.read_excel("/inputs/book.xlsx", parse_dates=["date"])
        date_index = df.columns.index("date")
        self.assertEqual(df.to_rows()[0][date_index], "dt:2025-01-01")

    def test_parse_dates_dict_is_supported(self):
        df = self.read_excel("/inputs/book.xlsx", parse_dates={"joined": ["date", "amount"]})
        joined_index = df.columns.index("joined")
        self.assertEqual(df.to_rows()[0][joined_index], "dt:2025-01-01 10")

    def test_na_true_false_values_are_supported(self):
        df = self.read_excel(
            "/inputs/book.xlsx",
            na_values=[None],
            true_values=["Y"],
            false_values=["N"],
        )
        flag_index = df.columns.index("flag")
        self.assertEqual(df.to_rows()[0][flag_index], True)
        self.assertEqual(df.to_rows()[1][flag_index], False)
        self.assertEqual(df.to_rows()[2][flag_index], "<NA>")

    def test_unsupported_option_raises(self):
        with self.assertRaises(NotImplementedError):
            self.read_excel("/inputs/book.xlsx", thousands=",")

    def test_skiprows_cases_fixture_supports_header_after_intro_rows(self):
        df = self.read_excel("/inputs/skiprows_cases.xlsx", skiprows=2)
        self.assertEqual(df.columns, ["id", "name", "score"])
        self.assertEqual(df.to_rows()[0], [1, "Alice", 91])

    def test_usecols_cases_fixture_supports_string_ranges_and_lists(self):
        df = self.read_excel("/inputs/usecols_cases.xlsx", usecols="B:D")
        self.assertEqual(df.columns, ["B_col", "C_col", "D_col"])
        self.assertEqual(df.to_rows()[1], [20, 30, 40])

    def test_usecols_cases_fixture_supports_column_index_list(self):
        df = self.read_excel("/inputs/usecols_cases.xlsx", usecols=[0, 2, 4])
        self.assertEqual(df.columns, ["A_col", "C_col", "E_col"])
        self.assertEqual(df.to_rows()[0], [1, 3, 5])

    def test_usecols_cases_fixture_supports_column_name_list(self):
        df = self.read_excel("/inputs/usecols_cases.xlsx", usecols=["B_col", "D_col"])
        self.assertEqual(df.columns, ["B_col", "D_col"])
        self.assertEqual(df.to_rows()[1], [20, 40])

    def test_usecols_cases_fixture_supports_callable_for_skipping_columns(self):
        df = self.read_excel("/inputs/usecols_cases.xlsx", usecols=lambda col: col not in {"B_col", "D_col"})
        self.assertEqual(df.columns, ["A_col", "C_col", "E_col"])
        self.assertEqual(df.to_rows()[0], [1, 3, 5])

    def test_dates_and_na_fixture_supports_parse_dates_and_na_maps(self):
        df = self.read_excel(
            "/inputs/dates_and_na.xlsx",
            parse_dates=["event_date", "end_date"],
            na_values=["missing", None],
            true_values=["Y"],
            false_values=["N"],
        )
        self.assertEqual(df.to_rows()[0], ["dt:2025-01-01", "dt:2025-01-03", True, "10"])
        self.assertEqual(df.to_rows()[1], ["dt:2025-02-01", "dt:<NA>", False, "<NA>"])

    def test_index_and_names_fixture_supports_multi_index_columns_and_names_override(self):
        df = self.read_excel(
            "/inputs/index_and_names.xlsx",
            names=["region_code", "store_code", "sales_amount", "cost_amount"],
            index_col=[0, 1],
        )
        self.assertEqual(df.columns, ["region_code", "store_code", "sales_amount", "cost_amount"])
        self.assertEqual(df.index_keys, ["region_code", "store_code"])

    def test_ragged_rows_fixture_is_padded(self):
        df = self.read_excel("/inputs/ragged_rows.xlsx")
        self.assertEqual(df.columns, ["c1", "c2", "c3", "c4"])
        self.assertEqual(df.to_rows(), [[1, 2, None, None], [3, 4, 5, None], [6, None, None, None]])

    def test_unicode_sheet_names_fixture_can_be_selected_by_name(self):
        result = self.read_excel("/inputs/unicode_sheet_names.xlsx", sheet_name=None)
        self.assertEqual(set(result.keys()), {"集計 シート", "祝日-2025"})
        self.assertEqual(result["集計 シート"].to_rows(), [["件数", 3]])

    def test_formula_like_cells_fixture_preserves_formula_like_strings(self):
        df = self.read_excel("/inputs/formula_like_cells.xlsx")
        self.assertEqual(df.to_rows()[0], ["=SUM(A1:B1)", "plain-text"])
        self.assertEqual(df.to_rows()[1], ["=A2*10", "still-text"])

    def test_header_none_cases_fixture_keeps_raw_rows(self):
        df = self.read_excel("/inputs/header_none_cases.xlsx", header=None)
        self.assertEqual(df.columns, [0, 1, 2])
        self.assertEqual(df.to_rows()[0], ["meta", "version1", None])
        self.assertEqual(df.to_rows()[2], [1, 2, 3])

    def test_combined_skiprows_and_header(self):
        df = self.read_excel("/inputs/skiprows_cases.xlsx", skiprows=2, header=0, nrows=2)
        self.assertEqual(df.columns, ["id", "name", "score"])
        self.assertEqual(df.to_rows(), [[1, "Alice", 91], [2, "Bob", 88]])

    def test_combined_usecols_and_names(self):
        df = self.read_excel(
            "/inputs/usecols_cases.xlsx",
            names=["a_value", "b_value", "c_value", "d_value", "e_value"],
            usecols=["b_value", "d_value"],
        )
        self.assertEqual(df.columns, ["b_value", "d_value"])
        self.assertEqual(df.to_rows()[0], [2, 4])

    def test_combined_usecols_and_index_col(self):
        df = self.read_excel(
            "/inputs/index_and_names.xlsx",
            usecols=["region", "store", "sales"],
            index_col=[0, 1],
        )
        self.assertEqual(df.columns, ["region", "store", "sales"])
        self.assertEqual(df.index_keys, ["region", "store"])
        self.assertEqual(df.to_rows()[1], ["East", "B", 120])

    def test_combined_na_values_and_parse_dates(self):
        df = self.read_excel(
            "/inputs/dates_and_na.xlsx",
            na_values=[None, "missing"],
            parse_dates=["event_date", "end_date"],
        )
        self.assertEqual(df.to_rows()[1], ["dt:2025-02-01", "dt:<NA>", "N", "<NA>"])

    def test_combined_header_none_names_and_nrows(self):
        df = self.read_excel(
            "/inputs/header_none_cases.xlsx",
            header=None,
            names=["kind", "value_a", "value_b"],
            nrows=2,
        )
        self.assertEqual(df.columns, ["kind", "value_a", "value_b"])
        self.assertEqual(df.to_rows(), [["meta", "version1", None], ["alpha", "beta", "gamma"]])

    def test_combined_sheet_name_none_and_parse_dates(self):
        result = self.read_excel("/inputs/dates_and_na.xlsx", sheet_name=None, parse_dates=["event_date"])
        self.assertEqual(set(result.keys()), {"DatesNA"})
        self.assertEqual(result["DatesNA"].to_rows()[0][0], "dt:2025-01-01")

    def test_fixture_book_workbook_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "book.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/book.xlsx"])

    def test_fixture_multi_header_workbook_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "multi_header.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/multi_header.xlsx"])

    def test_fixture_unicode_workbook_keeps_unicode_sheet_names_and_values(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "unicode.xlsx")
        self.assertEqual(workbook["sheetNames"], ["祝日", "集計"])
        self.assertEqual(workbook["sheets"]["祝日"][1], ["2025-01-01", "元日"])
        self.assertEqual(workbook["sheets"]["集計"][1], ["祝日", 2])

    def test_fixture_skiprows_cases_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "skiprows_cases.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/skiprows_cases.xlsx"])

    def test_fixture_usecols_cases_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "usecols_cases.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/usecols_cases.xlsx"])

    def test_fixture_dates_and_na_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "dates_and_na.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/dates_and_na.xlsx"])

    def test_fixture_index_and_names_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "index_and_names.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/index_and_names.xlsx"])

    def test_fixture_ragged_rows_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "ragged_rows.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/ragged_rows.xlsx"])

    def test_fixture_unicode_sheet_names_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "unicode_sheet_names.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/unicode_sheet_names.xlsx"])

    def test_fixture_formula_like_cells_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "formula_like_cells.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/formula_like_cells.xlsx"])

    def test_fixture_header_none_cases_matches_expected_rows(self):
        workbook = load_fixture_workbook(FIXTURES_DIR / "header_none_cases.xlsx")
        self.assertEqual(workbook, self.workbooks["/inputs/header_none_cases.xlsx"])


if __name__ == "__main__":
    unittest.main()
