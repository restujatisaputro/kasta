from decimal import Decimal

import pytest

from kasta_api.modules.ocr.constants import ReceiptFieldName
from kasta_api.modules.ocr.parser import IndonesianReceiptParser, parse_indonesian_money


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Rp25.000", Decimal("25000.00")),
        ("Rp 25.000", Decimal("25000.00")),
        ("25.000,00", Decimal("25000.00")),
        ("25,000", Decimal("25000.00")),
        ("25000", Decimal("25000.00")),
        ("Rp 1.250.500", Decimal("1250500.00")),
        ("12,50", Decimal("12.50")),
        ("-Rp 5.000", Decimal("-5000.00")),
    ],
)
def test_parse_indonesian_money_formats(raw: str, expected: Decimal) -> None:
    assert parse_indonesian_money(raw) == expected


def test_invalid_money_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_indonesian_money("dua puluh ribu")


@pytest.mark.parametrize("label", ["TOTAL", "GRAND TOTAL", "JUMLAH", "BAYAR"])
def test_supported_total_labels(label: str) -> None:
    parsed = IndonesianReceiptParser().parse(f"TOKO MAJU\n{label} Rp 25.000")
    assert parsed.value(ReceiptFieldName.TOTAL) == "25000.00"


def test_total_does_not_read_subtotal() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\nSUBTOTAL 20.000\nTOTAL 22.000")
    assert parsed.value(ReceiptFieldName.SUBTOTAL) == "20000.00"
    assert parsed.value(ReceiptFieldName.TOTAL) == "22000.00"


def test_discount_and_tax_are_extracted() -> None:
    parsed = IndonesianReceiptParser().parse(
        "TOKO MAJU\nSUBTOTAL 100.000\nDISKON 10.000\nPPN 9.000\nTOTAL 99.000"
    )
    assert parsed.value(ReceiptFieldName.DISCOUNT) == "10000.00"
    assert parsed.value(ReceiptFieldName.TAX) == "9000.00"


@pytest.mark.parametrize(
    ("keyword", "expected"),
    [
        ("TUNAI", "CASH"),
        ("QRIS", "QRIS"),
        ("TRANSFER", "BANK_TRANSFER"),
        ("DEBIT", "CARD"),
    ],
)
def test_payment_method_keywords(keyword: str, expected: str) -> None:
    parsed = IndonesianReceiptParser().parse(f"TOKO MAJU\nTOTAL 25.000\n{keyword} 25.000")
    assert parsed.value(ReceiptFieldName.PAYMENT_METHOD) == expected


def test_change_line_is_not_used_as_payment_method() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\nTUNAI 50.000\nKEMBALI TUNAI 5.000")
    assert parsed.value(ReceiptFieldName.PAYMENT_METHOD) == "CASH"


def test_numeric_indonesian_date_is_extracted() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\nTanggal: 21/07/2026\nTOTAL 25.000")
    assert parsed.value(ReceiptFieldName.RECEIPT_DATE) == "2026-07-21"


def test_iso_date_is_extracted() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\n2026-07-21\nTOTAL 25.000")
    assert parsed.value(ReceiptFieldName.RECEIPT_DATE) == "2026-07-21"


def test_textual_indonesian_date_is_extracted() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\n21 Juli 2026\nTOTAL 25.000")
    assert parsed.value(ReceiptFieldName.RECEIPT_DATE) == "2026-07-21"


@pytest.mark.parametrize(
    "line",
    ["No Nota: INV-2026/007", "Invoice #ABC-123", "TRX: QRS7788"],
)
def test_receipt_number_is_extracted(line: str) -> None:
    parsed = IndonesianReceiptParser().parse(f"TOKO MAJU\n{line}\nTOTAL 25.000")
    assert parsed.value(ReceiptFieldName.RECEIPT_NUMBER) is not None


def test_merchant_is_extracted_from_header() -> None:
    parsed = IndonesianReceiptParser().parse(
        "WARUNG SEDERHANA BU ANI\nJl. Mawar No. 2\nTOTAL Rp 25.000"
    )
    assert parsed.value(ReceiptFieldName.MERCHANT_NAME) == "WARUNG SEDERHANA BU ANI"


def test_simple_item_is_extracted() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\nMinyak Goreng 25.000\nTOTAL 25.000")
    assert len(parsed.items) == 1
    assert parsed.items[0].description == "Minyak Goreng"
    assert parsed.items[0].line_total == Decimal("25000.00")


def test_quantity_item_is_extracted() -> None:
    parsed = IndonesianReceiptParser().parse(
        "TOKO MAJU\nAir Mineral 2 x 5.000 10.000\nTOTAL 10.000"
    )
    assert len(parsed.items) == 1
    assert parsed.items[0].quantity == Decimal("2.00")
    assert parsed.items[0].unit_price == Decimal("5000.00")
    assert parsed.items[0].line_total == Decimal("10000.00")


def test_summary_lines_are_not_items() -> None:
    parsed = IndonesianReceiptParser().parse(
        "TOKO MAJU\nRoti 10.000\nSUBTOTAL 10.000\nDISKON 1.000\nTOTAL 9.000"
    )
    assert [item.description for item in parsed.items] == ["Roti"]


def test_transport_category_is_recommended() -> None:
    parsed = IndonesianReceiptParser().parse("SPBU 34\nPERTALITE 50.000\nTOTAL 50.000")
    assert parsed.value(ReceiptFieldName.CATEGORY_ACCOUNT) == "TRANSPORTATION"


def test_raw_material_category_is_recommended() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO BAHAN\nTepung 50.000\nTOTAL 50.000")
    assert parsed.value(ReceiptFieldName.CATEGORY_ACCOUNT) == "RAW_MATERIALS"


def test_default_category_is_purchases() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\nProduk A 50.000\nTOTAL 50.000")
    assert parsed.value(ReceiptFieldName.CATEGORY_ACCOUNT) == "PURCHASES"


def test_sales_marker_recommends_income() -> None:
    parsed = IndonesianReceiptParser().parse(
        "TOKO MAJU\nSALES RECEIPT\nProduk A 50.000\nTOTAL 50.000"
    )
    assert parsed.value(ReceiptFieldName.TRANSACTION_KIND) == "INCOME"


def test_receipt_defaults_to_expense() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\nProduk A 50.000\nTOTAL 50.000")
    assert parsed.value(ReceiptFieldName.TRANSACTION_KIND) == "EXPENSE"


def test_empty_ocr_returns_no_financial_fields() -> None:
    parsed = IndonesianReceiptParser().parse("")
    assert parsed.fields == {}
    assert parsed.items == []


def test_confidence_is_recorded_per_field() -> None:
    parsed = IndonesianReceiptParser().parse("TOKO MAJU\nTOTAL Rp25.000\nQRIS")
    assert parsed.fields[ReceiptFieldName.TOTAL].confidence == Decimal("0.96")
    assert parsed.fields[ReceiptFieldName.PAYMENT_METHOD].confidence == Decimal("0.96")
