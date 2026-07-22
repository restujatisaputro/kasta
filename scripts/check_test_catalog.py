"""Validate the test catalogue used as the KASTA QA release gate.

The catalogue is intentionally kept in Markdown so it is readable by product and QA
teams.  This small, dependency-free check prevents a documentation-only change from
silently dropping a critical scenario or one of the requested test layers.
"""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = REPOSITORY_ROOT / "documentation/testing/test-cases.md"

REQUIRED_COLUMNS = {
    "ID",
    "Jenis test",
    "Modul",
    "Tujuan",
    "Prasyarat",
    "Langkah",
    "Hasil yang diharapkan",
    "Hasil aktual",
    "Status",
    "Catatan",
    "Penguji",
    "Tanggal",
    "Severity",
    "Priority",
}

REQUIRED_TYPES = {
    "Unit",
    "Integration",
    "API",
    "Database",
    "Tenant isolation",
    "RLS",
    "Accounting",
    "OCR",
    "Sync",
    "Offline",
    "Android UI",
    "Component",
    "End-to-end",
    "Accessibility",
    "Performance",
    "Load",
    "Security",
    "Backup/restore",
}

REQUIRED_SCENARIOS = {
    "Jurnal seimbang",
    "Transaksi dibatalkan",
    "Pembayaran sebagian",
    "Nota duplikat",
    "Pembina tanpa izin",
    "Izin pembina kedaluwarsa",
    "Pengguna dua perangkat",
    "Konflik transaksi",
    "Jaringan terputus",
    "Upload nota gagal",
    "OCR confidence rendah",
    "Data Usaha A tidak terlihat Usaha B",
}


def _table_rows(markdown: str) -> tuple[list[str], list[list[str]]]:
    """Read the first Markdown table after the catalogue heading."""

    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|") or index + 1 >= len(lines):
            continue
        separator = lines[index + 1]
        if not re.fullmatch(r"\s*\|?(?:\s*:?-+:?\s*\|)+\s*", separator):
            continue
        headers = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows: list[list[str]] = []
        for row in lines[index + 2 :]:
            if not row.lstrip().startswith("|"):
                break
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
            if len(cells) == len(headers):
                rows.append(cells)
        return headers, rows
    raise ValueError("catalogue table was not found")


def main() -> int:
    errors: list[str] = []
    try:
        markdown = CATALOGUE.read_text(encoding="utf-8")
        headers, rows = _table_rows(markdown)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Test catalogue tidak dapat dibaca: {error}")
        return 1

    missing_columns = REQUIRED_COLUMNS - set(headers)
    if missing_columns:
        errors.append(f"kolom wajib hilang: {', '.join(sorted(missing_columns))}")
    if not rows:
        errors.append("tidak ada test case")

    by_header = {header: index for index, header in enumerate(headers)}
    statuses = {"PASS", "FAIL", "BLOCKED", "NOT RUN"}
    severities = {"Critical", "High", "Medium", "Low"}
    priorities = {"P0", "P1", "P2", "P3"}
    seen_ids: set[str] = set()
    # The human-readable type column may say "Unit" while the module says OCR
    # parser or offline sync.  Search the whole row so those layers remain
    # traceable without forcing awkward duplicate labels into the matrix.
    joined_types = "\n".join(" ".join(row) for row in rows)

    for row_number, row in enumerate(rows, start=1):
        test_id = row[by_header["ID"]]
        if not test_id or test_id in seen_ids:
            errors.append(f"baris {row_number}: ID kosong atau duplikat ({test_id!r})")
        seen_ids.add(test_id)
        for column in ("Modul", "Tujuan", "Prasyarat", "Langkah", "Hasil yang diharapkan"):
            if not row[by_header[column]]:
                errors.append(f"baris {row_number}: {column} kosong")
        if row[by_header["Status"]] not in statuses:
            errors.append(f"baris {row_number}: status tidak valid")
        if row[by_header["Severity"]] not in severities:
            errors.append(f"baris {row_number}: severity tidak valid")
        if row[by_header["Priority"]] not in priorities:
            errors.append(f"baris {row_number}: priority tidak valid")

    missing_types = {
        test_type for test_type in REQUIRED_TYPES if test_type.lower() not in joined_types.lower()
    }
    if missing_types:
        errors.append(f"jenis test wajib hilang: {', '.join(sorted(missing_types))}")

    traceability = markdown.split("## Traceability skenario wajib", 1)
    trace_text = traceability[1] if len(traceability) == 2 else ""
    missing_scenarios = {
        scenario for scenario in REQUIRED_SCENARIOS if scenario.lower() not in trace_text.lower()
    }
    if missing_scenarios:
        errors.append(f"skenario wajib hilang: {', '.join(sorted(missing_scenarios))}")

    if errors:
        print("Test catalogue KASTA tidak valid:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Test catalogue valid: {len(rows)} kasus, {len(REQUIRED_TYPES)} lapisan test terpetakan."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
