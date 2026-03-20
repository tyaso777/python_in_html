from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


WORKBOOKS = {
    "book.xlsx": {
        "sheet_names": ["Main", "Second"],
        "sheets": {
            "Main": [
                ["id", "name", "flag", "date", "amount"],
                [1, "Alice", "Y", "2025-01-01", "10"],
                [2, "Bob", "N", "2025-01-02", "20"],
                [3, "Carol", "", "2025-01-03", "30"],
            ],
            "Second": [
                ["code", "value"],
                ["A", 100],
                ["B", 200],
            ],
        },
    },
    "multi_header.xlsx": {
        "sheet_names": ["Sheet1"],
        "sheets": {
            "Sheet1": [
                ["group", "group", "meta"],
                ["left", "right", "value"],
                [1, 2, 3],
            ],
        },
    },
    "unicode.xlsx": {
        "sheet_names": ["祝日", "集計"],
        "sheets": {
            "祝日": [
                ["日付", "名称"],
                ["2025-01-01", "元日"],
                ["2025-02-11", "建国記念の日"],
            ],
            "集計": [
                ["区分", "件数"],
                ["祝日", 2],
            ],
        },
    },
    "skiprows_cases.xlsx": {
        "sheet_names": ["SkipRows"],
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
    "usecols_cases.xlsx": {
        "sheet_names": ["Wide"],
        "sheets": {
            "Wide": [
                ["A_col", "B_col", "C_col", "D_col", "E_col"],
                [1, 2, 3, 4, 5],
                [10, 20, 30, 40, 50],
            ],
        },
    },
    "dates_and_na.xlsx": {
        "sheet_names": ["DatesNA"],
        "sheets": {
            "DatesNA": [
                ["event_date", "end_date", "flag", "amount"],
                ["2025-01-01", "2025-01-03", "Y", "10"],
                ["2025-02-01", None, "N", "missing"],
                ["2025-03-01", "2025-03-05", None, "30"],
            ],
        },
    },
    "index_and_names.xlsx": {
        "sheet_names": ["Indexed"],
        "sheets": {
            "Indexed": [
                ["region", "store", "sales", "cost"],
                ["East", "A", 100, 70],
                ["East", "B", 120, 80],
                ["West", "C", 90, 60],
            ],
        },
    },
    "ragged_rows.xlsx": {
        "sheet_names": ["Ragged"],
        "sheets": {
            "Ragged": [
                ["c1", "c2", "c3", "c4"],
                [1, 2],
                [3, 4, 5],
                [6],
            ],
        },
    },
    "unicode_sheet_names.xlsx": {
        "sheet_names": ["集計 シート", "祝日-2025"],
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
    "formula_like_cells.xlsx": {
        "sheet_names": ["FormulaLike"],
        "sheets": {
            "FormulaLike": [
                ["expr", "literal"],
                ["=SUM(A1:B1)", "plain-text"],
                ["=A2*10", "still-text"],
            ],
        },
    },
    "header_none_cases.xlsx": {
        "sheet_names": ["RawRows"],
        "sheets": {
            "RawRows": [
                ["meta", "version1", None],
                ["alpha", "beta", "gamma"],
                [1, 2, 3],
            ],
        },
    },
}


def column_name(index: int) -> str:
    result = ""
    current = index + 1
    while current:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def sheet_xml(rows: list[list[object]]) -> str:
    row_parts = []
    for row_idx, row in enumerate(rows, start=1):
        cell_parts = []
        for col_idx, value in enumerate(row):
            ref = f"{column_name(col_idx)}{row_idx}"
            if value is None:
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cell_parts.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                text = escape(str(value))
                cell_parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        row_parts.append(f'<row r="{row_idx}">{"".join(cell_parts)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_parts)}</sheetData>'
        "</worksheet>"
    )


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = []
    for idx, name in enumerate(sheet_names, start=1):
        sheets.append(
            f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(sheets)}</sheets>'
        "</workbook>"
    )


def workbook_rels_xml(sheet_names: list[str]) -> str:
    parts = []
    for idx, _name in enumerate(sheet_names, start=1):
        parts.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
    parts.append(
        '<Relationship Id="rIdStyles" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(parts)}'
        "</Relationships>"
    )


def root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def content_types_xml(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for idx in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'{"".join(overrides)}'
        "</Types>"
    )


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="1"><xf xfId="0"/></cellXfs>'
        "</styleSheet>"
    )


def write_workbook(path: Path, workbook: dict[str, object]) -> None:
    sheet_names = workbook["sheet_names"]
    sheets = workbook["sheets"]
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(len(sheet_names)))
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("xl/workbook.xml", workbook_xml(sheet_names))
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(sheet_names))
        zf.writestr("xl/styles.xml", styles_xml())
        for idx, sheet_name in enumerate(sheet_names, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", sheet_xml(sheets[sheet_name]))


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    for file_name, workbook in WORKBOOKS.items():
        write_workbook(FIXTURES_DIR / file_name, workbook)


if __name__ == "__main__":
    main()
