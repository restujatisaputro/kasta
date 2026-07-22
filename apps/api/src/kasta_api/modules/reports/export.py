import csv
from decimal import Decimal
from io import BytesIO, StringIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from kasta_api.modules.reports.schemas import FinancialReportResponse

CellRow = list[object] | list[str]


def build_report_csv(report: FinancialReportResponse) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Laporan KASTA", report.context.business_name])
    writer.writerow(["Periode", report.context.date_from, report.context.date_to])
    writer.writerow(["Sumber angka keuangan", "Jurnal double-entry"])
    writer.writerow([])
    writer.writerow(["Bagian", "Rincian", "Nilai", "Keterangan"])
    for row in _flat_rows(report):
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def build_report_xlsx(report: FinancialReportResponse) -> bytes:
    sheets: list[tuple[str, list[CellRow]]] = [
        (
            "Ringkasan",
            [
                ["Laporan KASTA", report.context.business_name],
                ["Periode", str(report.context.date_from), str(report.context.date_to)],
                ["Sumber", "Jurnal double-entry"],
                [],
                ["Ukuran", "Nilai"],
                ["Pemasukan", report.summary.income],
                ["Pengeluaran", report.summary.expense],
                ["Perkiraan laba", report.summary.estimated_profit],
                ["Uang masuk", report.summary.cash_in],
                ["Uang keluar", report.summary.cash_out],
                ["Arus kas bersih", report.summary.net_cash_flow],
                ["Piutang", report.summary.receivables],
                ["Utang", report.summary.payables],
                ["Persediaan", report.summary.inventory_value],
                [],
                ["Penjelasan", report.explanation],
            ],
        ),
        (
            "Laba Rugi",
            [["Kelompok", "Akun", "Nilai"]]
            + [["Pemasukan", row.account_name, row.amount] for row in report.profit_loss.revenues]
            + [["Pengeluaran", row.account_name, row.amount] for row in report.profit_loss.expenses]
            + [[], ["Laba/Rugi", "", report.profit_loss.profit]],
        ),
        (
            "Posisi Keuangan",
            [["Kelompok", "Akun", "Nilai"]]
            + [["Aset", row.account_name, row.amount] for row in report.balance_sheet.assets]
            + [["Utang", row.account_name, row.amount] for row in report.balance_sheet.liabilities]
            + [["Modal", row.account_name, row.amount] for row in report.balance_sheet.equity]
            + [
                [],
                ["Total aset", "", report.balance_sheet.total_assets],
                ["Total utang", "", report.balance_sheet.total_liabilities],
                ["Total modal dan laba", "", report.balance_sheet.total_equity],
            ],
        ),
        (
            "Arus Kas",
            [
                ["Rincian", "Nilai"],
                ["Uang masuk", report.cash_flow.cash_in],
                ["Uang keluar", report.cash_flow.cash_out],
                ["Perubahan bersih", report.cash_flow.net_cash_flow],
                ["Saldo kas akhir", report.cash_flow.ending_cash_balance],
                [],
                ["Penjelasan", report.cash_flow.explanation],
            ],
        ),
        (
            "Kategori",
            [["Jenis", "Kategori", "Nilai", "Persentase"]]
            + [["Penjualan", row.label, row.amount, row.percentage] for row in report.sales]
            + [
                ["Pengeluaran", row.label, row.amount, row.percentage]
                for row in report.expenditures
            ],
        ),
        (
            "Utang Piutang",
            [
                [
                    "Jenis",
                    "Belum lunas",
                    "Terlambat",
                    "Nilai awal",
                    "Sudah dibayar",
                    "Sisa daftar",
                    "Saldo jurnal",
                ],
                [
                    "Piutang",
                    report.receivables.open_count,
                    report.receivables.overdue_count,
                    report.receivables.total_initial,
                    report.receivables.total_paid,
                    report.receivables.total_remaining,
                    report.receivables.journal_value,
                ],
                [
                    "Utang",
                    report.payables.open_count,
                    report.payables.overdue_count,
                    report.payables.total_initial,
                    report.payables.total_paid,
                    report.payables.total_remaining,
                    report.payables.journal_value,
                ],
            ],
        ),
        (
            "Produk Terlaris",
            [["SKU", "Produk", "Satuan", "Jumlah terjual", "Nilai penjualan"]]
            + [
                [item.sku, item.name, item.unit, item.quantity_sold, item.sales_value]
                for item in report.best_selling_products
            ],
        ),
        (
            "Perbandingan Bulanan",
            [["Bulan", "Pemasukan", "Pengeluaran", "Laba", "Penjualan"]]
            + [
                [item.period, item.income, item.expense, item.profit, item.sales]
                for item in report.monthly_comparison
            ],
        ),
    ]
    return _xlsx(sheets)


def build_report_pdf(report: FinancialReportResponse) -> bytes:
    lines = [
        f"LAPORAN KASTA - {report.context.business_name}",
        f"Periode: {report.context.date_from} sampai {report.context.date_to}",
        "Sumber angka keuangan: jurnal double-entry",
        "",
        report.explanation,
        "",
        "RINGKASAN",
        f"Pemasukan: {_rupiah(report.summary.income)}",
        f"Pengeluaran: {_rupiah(report.summary.expense)}",
        f"Perkiraan laba/rugi: {_rupiah(report.summary.estimated_profit)}",
        f"Uang masuk: {_rupiah(report.summary.cash_in)}",
        f"Uang keluar: {_rupiah(report.summary.cash_out)}",
        f"Piutang belum lunas: {_rupiah(report.summary.receivables)}",
        f"Utang belum lunas: {_rupiah(report.summary.payables)}",
        f"Nilai persediaan: {_rupiah(report.summary.inventory_value)}",
        "",
        "LABA RUGI",
    ]
    lines.extend(
        f"Pemasukan - {row.account_name}: {_rupiah(row.amount)}"
        for row in report.profit_loss.revenues
    )
    lines.extend(
        f"Pengeluaran - {row.account_name}: {_rupiah(row.amount)}"
        for row in report.profit_loss.expenses
    )
    lines.extend([report.profit_loss.explanation, "", "POSISI KEUANGAN"])
    lines.extend(
        f"Aset - {row.account_name}: {_rupiah(row.amount)}" for row in report.balance_sheet.assets
    )
    lines.extend(
        f"Utang - {row.account_name}: {_rupiah(row.amount)}"
        for row in report.balance_sheet.liabilities
    )
    lines.extend(
        f"Modal - {row.account_name}: {_rupiah(row.amount)}" for row in report.balance_sheet.equity
    )
    lines.extend([report.balance_sheet.explanation, "", "ARUS KAS", report.cash_flow.explanation])
    lines.extend(
        ["", "UTANG DAN PIUTANG", report.receivables.explanation, report.payables.explanation]
    )
    lines.extend(["", "PERSEDIAAN", report.inventory.explanation, "", "PRODUK TERLARIS"])
    lines.extend(
        f"{index}. {item.name}: {item.quantity_sold} {item.unit} / {_rupiah(item.sales_value)}"
        for index, item in enumerate(report.best_selling_products, start=1)
    )
    return _pdf(lines)


def _flat_rows(report: FinancialReportResponse) -> list[list[object]]:
    rows: list[list[object]] = [
        ["Ringkasan", "Pemasukan", report.summary.income, report.explanation],
        ["Ringkasan", "Pengeluaran", report.summary.expense, ""],
        ["Ringkasan", "Perkiraan laba", report.summary.estimated_profit, ""],
        ["Arus kas", "Uang masuk", report.summary.cash_in, report.cash_flow.explanation],
        ["Arus kas", "Uang keluar", report.summary.cash_out, ""],
        [
            "Piutang",
            "Saldo jurnal",
            report.receivables.journal_value,
            report.receivables.explanation,
        ],
        ["Utang", "Saldo jurnal", report.payables.journal_value, report.payables.explanation],
        [
            "Persediaan",
            "Saldo jurnal",
            report.inventory.journal_value,
            report.inventory.explanation,
        ],
    ]
    rows.extend(
        ["Pemasukan", row.account_name, row.amount, ""] for row in report.profit_loss.revenues
    )
    rows.extend(
        ["Pengeluaran", row.account_name, row.amount, ""] for row in report.profit_loss.expenses
    )
    rows.extend(
        ["Produk terlaris", row.name, row.sales_value, f"{row.quantity_sold} {row.unit}"]
        for row in report.best_selling_products
    )
    rows.extend(
        [
            "Perbandingan bulanan",
            row.period,
            row.profit,
            f"Masuk {row.income}; keluar {row.expense}",
        ]
        for row in report.monthly_comparison
    )
    return rows


def _xlsx(sheets: list[tuple[str, list[CellRow]]]) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_relationships())
        archive.writestr("xl/workbook.xml", _workbook(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships(len(sheets)))
        archive.writestr("xl/styles.xml", _styles())
        for index, (_, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet(rows))
    return output.getvalue()


def _sheet(rows: list[CellRow]) -> str:
    xml_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row, start=1):
            reference = f"{_column(column_index)}{row_index}"
            if isinstance(value, (int, float)) or value.__class__.__name__ == "Decimal":
                cells.append(f'<c r="{reference}" t="n"><v>{value}</v></c>')
            else:
                cells.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
                )
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<cols><col min="1" max="12" width="24" customWidth="1"/></cols>'
        f"<sheetData>{''.join(xml_rows)}</sheetData></worksheet>"
    )


def _content_types(count: int) -> str:
    sheets = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.styles+xml"/>'
        f"{sheets}</Types>"
    )


def _root_relationships() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook(sheets: list[tuple[str, list[CellRow]]]) -> str:
    nodes = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _) in enumerate(sheets, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{nodes}</sheets></workbook>"
    )


def _workbook_relationships(count: int) -> str:
    nodes = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{nodes}<Relationship Id="rId{count + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/></Relationships>'
    )


def _styles() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Arial"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellXfs>'
        "</styleSheet>"
    )


def _column(index: int) -> str:
    value = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        value = chr(65 + remainder) + value
    return value


def _pdf(lines: list[str]) -> bytes:
    chunks = [lines[index : index + 44] for index in range(0, len(lines), 44)] or [[]]
    page_count = len(chunks)
    font_id = 3 + page_count * 2
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(page_count))
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>").encode(),
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, page_lines in enumerate(chunks):
        page_id = 3 + index * 2
        content_id = page_id + 1
        commands = ["BT", "/F1 10 Tf", "48 794 Td", "13 TL"]
        for line in page_lines:
            safe = line.encode("latin-1", "replace").decode("latin-1")
            safe = safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.extend([f"({safe}) Tj", "T*"])
        commands.append("ET")
        content = "\n".join(commands).encode("latin-1")
        objects[content_id] = (
            f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id in range(1, font_id + 1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode())
        output.extend(objects[object_id])
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {font_id + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {font_id + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


def _rupiah(value: Decimal) -> str:
    whole = int(value)
    sign = "-" if whole < 0 else ""
    return f"{sign}Rp{abs(whole):,}".replace(",", ".")
