from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from kasta_api.modules.inventory.models import Product

PACKAGE_RELATIONSHIPS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOCUMENT_RELATIONSHIPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SPREADSHEET_CONTENT = "application/vnd.openxmlformats-officedocument.spreadsheetml"


def build_products_xlsx(products: list[Product]) -> bytes:
    headers = (
        "SKU",
        "Barcode",
        "Nama",
        "Kategori",
        "Satuan",
        "Harga Beli",
        "Harga Jual",
        "Stok Awal",
        "Stok Saat Ini",
        "Stok Minimum",
        "Aktif",
        "Nilai Persediaan",
    )
    rows: list[list[tuple[str, bool]]] = [[(value, False) for value in headers]]
    for product in products:
        rows.append(
            [
                (product.sku, False),
                (product.barcode or "", False),
                (product.name, False),
                (product.category, False),
                (product.unit, False),
                (str(product.purchase_price), True),
                (str(product.sale_price), True),
                (str(product.opening_stock), True),
                (str(product.current_stock), True),
                (str(product.minimum_stock), True),
                ("Ya" if product.is_active else "Tidak", False),
                (str(product.current_stock * product.purchase_price), True),
            ]
        )
    sheet_rows = []
    for row_number, row in enumerate(rows, start=1):
        cells = []
        for column_number, (value, numeric) in enumerate(row, start=1):
            reference = f"{_column_name(column_number)}{row_number}"
            if numeric:
                cells.append(f'<c r="{reference}" s="1"><v>{escape(value)}</v></c>')
            else:
                cells.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
                )
        sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<cols><col min="1" max="12" width="18" customWidth="1"/></cols>'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" ContentType="{SPREADSHEET_CONTENT}'
            '.sheet.main+xml"/>'
            f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{SPREADSHEET_CONTENT}'
            '.worksheet+xml"/>'
            f'<Override PartName="/xl/styles.xml" ContentType="{SPREADSHEET_CONTENT}'
            '.styles+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Relationships xmlns="{PACKAGE_RELATIONSHIPS}">'
            f'<Relationship Id="rId1" Type="{DOCUMENT_RELATIONSHIPS}/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Produk dan Stok" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Relationships xmlns="{PACKAGE_RELATIONSHIPS}">'
            f'<Relationship Id="rId1" Type="{DOCUMENT_RELATIONSHIPS}/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{DOCUMENT_RELATIONSHIPS}/styles" '
            'Target="styles.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
            '<cellXfs count="2"><xf/><xf numFmtId="4" applyNumberFormat="1"/></cellXfs>'
            "</styleSheet>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name
