from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from kasta_api.modules.ocr.constants import ReceiptFieldName

MONEY_TOKEN = r"(?:RP\s*)?-?\d{1,3}(?:(?:[.,]\d{3})+|[.,]\d{2})|(?:RP\s*)?-?\d+"
MONEY_RE = re.compile(rf"(?<![A-Z0-9])({MONEY_TOKEN})(?![A-Z0-9])", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(?:(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})|(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4}))\b"
)
TEXTUAL_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(JAN(?:UARI)?|FEB(?:RUARI)?|MAR(?:ET)?|APR(?:IL)?|MEI|JUN(?:I)?|"
    r"JUL(?:I)?|AGU(?:STUS)?|SEP(?:TEMBER)?|OKT(?:OBER)?|NOV(?:EMBER)?|DES(?:EMBER)?)\s+"
    r"(\d{2,4})\b",
    re.IGNORECASE,
)
RECEIPT_NUMBER_RE = re.compile(
    r"\b(?:NO\.?\s*(?:NOTA|STRUK|TRANSAKSI)?|NOTA|INVOICE|INV|RECEIPT|TRX)\s*[:#-]?\s*"
    r"([A-Z0-9][A-Z0-9./-]{2,})\b",
    re.IGNORECASE,
)

MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MEI": 5,
    "JUN": 6,
    "JUL": 7,
    "AGU": 8,
    "SEP": 9,
    "OKT": 10,
    "NOV": 11,
    "DES": 12,
}

TOTAL_LABELS = ("GRAND TOTAL", "TOTAL", "JUMLAH", "BAYAR")
SUMMARY_LABELS = (*TOTAL_LABELS, "SUBTOTAL", "SUB TOTAL", "DISKON", "DISC", "PAJAK", "PPN")
PAYMENT_KEYWORDS = {
    "QRIS": "QRIS",
    "TRANSFER": "BANK_TRANSFER",
    "DEBIT": "CARD",
    "KARTU": "CARD",
    "TUNAI": "CASH",
    "CASH": "CASH",
}


@dataclass(frozen=True, slots=True)
class ParsedField:
    value: str
    confidence: Decimal
    source_text: str


@dataclass(frozen=True, slots=True)
class ParsedReceiptItem:
    line_number: int
    description: str
    quantity: Decimal | None
    unit_price: Decimal | None
    line_total: Decimal
    confidence: Decimal


@dataclass(slots=True)
class ParsedReceipt:
    fields: dict[str, ParsedField] = field(default_factory=dict)
    items: list[ParsedReceiptItem] = field(default_factory=list)

    def value(self, name: ReceiptFieldName | str) -> str | None:
        key = name.value if isinstance(name, ReceiptFieldName) else name
        extracted = self.fields.get(key)
        return extracted.value if extracted is not None else None


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).replace("\u00a0", " ")
    return re.sub(r"[ \t]+", " ", normalized).strip()


def normalize_match(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character for character in plain if not unicodedata.combining(character)
    )
    return re.sub(r"[^A-Z0-9]", "", without_marks.upper())


def parse_indonesian_money(value: str) -> Decimal:
    cleaned = normalize_text(value).upper().replace("RP", "").replace(" ", "")
    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("-+")
    if not cleaned or not re.fullmatch(r"\d+(?:[.,]\d+)*", cleaned):
        raise ValueError(f"Format nilai tidak dikenali: {value}")

    last_dot = cleaned.rfind(".")
    last_comma = cleaned.rfind(",")
    separator_index = max(last_dot, last_comma)
    decimal_part = ""
    integer_part = cleaned
    if separator_index >= 0:
        trailing = cleaned[separator_index + 1 :]
        separators = cleaned.count(".") + cleaned.count(",")
        if len(trailing) == 2 and (separators == 1 or last_dot != last_comma):
            integer_part = cleaned[:separator_index]
            decimal_part = trailing
    integer_digits = re.sub(r"[.,]", "", integer_part)
    try:
        amount = Decimal(f"{integer_digits}.{decimal_part or '00'}")
    except InvalidOperation as exc:
        raise ValueError(f"Format nilai tidak dikenali: {value}") from exc
    return -amount if negative else amount


class IndonesianReceiptParser:
    def parse(self, raw_text: str) -> ParsedReceipt:
        lines = [normalize_text(line) for line in raw_text.splitlines() if normalize_text(line)]
        result = ParsedReceipt()
        if not lines:
            return result

        merchant = self._merchant(lines)
        if merchant is not None:
            result.fields[ReceiptFieldName.MERCHANT_NAME] = merchant
        receipt_date = self._date(lines)
        if receipt_date is not None:
            result.fields[ReceiptFieldName.RECEIPT_DATE] = receipt_date
        receipt_number = self._receipt_number(lines)
        if receipt_number is not None:
            result.fields[ReceiptFieldName.RECEIPT_NUMBER] = receipt_number

        for field_name, labels in (
            (ReceiptFieldName.SUBTOTAL, ("SUBTOTAL", "SUB TOTAL")),
            (ReceiptFieldName.DISCOUNT, ("DISKON", "DISC", "DISCOUNT")),
            (ReceiptFieldName.TAX, ("PAJAK", "PPN", "TAX")),
        ):
            extracted = self._labelled_money(lines, labels)
            if extracted is not None:
                result.fields[field_name] = extracted
        total = self._total(lines)
        if total is not None:
            result.fields[ReceiptFieldName.TOTAL] = total

        payment = self._payment_method(lines)
        if payment is not None:
            result.fields[ReceiptFieldName.PAYMENT_METHOD] = payment
        transaction_kind = self._transaction_kind(lines)
        result.fields[ReceiptFieldName.TRANSACTION_KIND] = transaction_kind
        result.items = self._items(lines)
        category = self._category(lines, result.items)
        result.fields[ReceiptFieldName.CATEGORY_ACCOUNT] = category
        return result

    def _merchant(self, lines: list[str]) -> ParsedField | None:
        ignored = (
            "ALAMAT",
            "TELP",
            "PHONE",
            "NPWP",
            "NOTA",
            "INVOICE",
            "RECEIPT",
            "TANGGAL",
            "DATE",
            *SUMMARY_LABELS,
        )
        for index, line in enumerate(lines[:8]):
            upper = line.upper()
            if any(token in upper for token in ignored):
                continue
            if DATE_RE.search(line) or MONEY_RE.fullmatch(line):
                continue
            letters = sum(character.isalpha() for character in line)
            if letters >= 3 and len(line) <= 80:
                confidence = Decimal("0.92") if index == 0 else Decimal("0.78")
                return ParsedField(line, confidence, line)
        return None

    def _date(self, lines: list[str]) -> ParsedField | None:
        for line in lines:
            match = DATE_RE.search(line)
            if match:
                try:
                    if match.group(1):
                        parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                    else:
                        year = int(match.group(6))
                        if year < 100:
                            year += 2000
                        parsed = date(year, int(match.group(5)), int(match.group(4)))
                except ValueError:
                    continue
                confidence = Decimal("0.97") if "TANGGAL" in line.upper() else Decimal("0.90")
                return ParsedField(parsed.isoformat(), confidence, line)
            textual = TEXTUAL_DATE_RE.search(line)
            if textual:
                year = int(textual.group(3))
                if year < 100:
                    year += 2000
                month = MONTHS[textual.group(2)[:3].upper()]
                try:
                    parsed = date(year, month, int(textual.group(1)))
                except ValueError:
                    continue
                return ParsedField(parsed.isoformat(), Decimal("0.92"), line)
        return None

    def _receipt_number(self, lines: list[str]) -> ParsedField | None:
        for line in lines:
            match = RECEIPT_NUMBER_RE.search(line.upper())
            if match:
                return ParsedField(match.group(1), Decimal("0.94"), line)
        return None

    def _labelled_money(self, lines: list[str], labels: tuple[str, ...]) -> ParsedField | None:
        for line in reversed(lines):
            upper = line.upper()
            if not any(label in upper for label in labels):
                continue
            amounts = self._money_values(line)
            if amounts:
                value, source = amounts[-1]
                return ParsedField(f"{abs(value):.2f}", Decimal("0.94"), source)
        return None

    def _total(self, lines: list[str]) -> ParsedField | None:
        for label_index, label in enumerate(TOTAL_LABELS):
            for line in reversed(lines):
                upper = line.upper()
                if label == "TOTAL" and ("SUBTOTAL" in upper or "SUB TOTAL" in upper):
                    continue
                if not re.search(rf"\b{re.escape(label)}\b", upper):
                    continue
                amounts = self._money_values(line)
                if amounts:
                    value, source = amounts[-1]
                    confidence = Decimal("0.99") - Decimal(label_index) * Decimal("0.03")
                    return ParsedField(f"{abs(value):.2f}", confidence, source)
        return None

    def _payment_method(self, lines: list[str]) -> ParsedField | None:
        for line in reversed(lines):
            upper = line.upper()
            if "KEMBALI" in upper:
                continue
            for keyword, method in PAYMENT_KEYWORDS.items():
                if re.search(rf"\b{keyword}\b", upper):
                    confidence = (
                        Decimal("0.96") if keyword in {"QRIS", "TRANSFER"} else Decimal("0.90")
                    )
                    return ParsedField(method, confidence, line)
        return None

    def _transaction_kind(self, lines: list[str]) -> ParsedField:
        combined = " ".join(lines).upper()
        income_markers = ("PENJUALAN", "SALES RECEIPT", "PELANGGAN", "CUSTOMER")
        if any(marker in combined for marker in income_markers):
            return ParsedField("INCOME", Decimal("0.72"), "Kata kunci penjualan")
        return ParsedField("EXPENSE", Decimal("0.82"), "Nota pembelian")

    def _items(self, lines: list[str]) -> list[ParsedReceiptItem]:
        items: list[ParsedReceiptItem] = []
        quantity_pattern = re.compile(
            rf"^(.*?)\s+(\d+(?:[.,]\d+)?)\s*[Xx@]\s*({MONEY_TOKEN})\s+({MONEY_TOKEN})\s*$",
            re.IGNORECASE,
        )
        simple_pattern = re.compile(rf"^(.*?)\s+({MONEY_TOKEN})\s*$", re.IGNORECASE)
        for index, line in enumerate(lines, start=1):
            upper = line.upper()
            if any(label in upper for label in SUMMARY_LABELS) or "KEMBALI" in upper:
                continue
            quantity_match = quantity_pattern.match(line)
            if quantity_match and self._valid_description(quantity_match.group(1)):
                items.append(
                    ParsedReceiptItem(
                        line_number=index,
                        description=quantity_match.group(1).strip(" .:-"),
                        quantity=parse_indonesian_money(quantity_match.group(2)),
                        unit_price=abs(parse_indonesian_money(quantity_match.group(3))),
                        line_total=abs(parse_indonesian_money(quantity_match.group(4))),
                        confidence=Decimal("0.92"),
                    )
                )
                continue
            simple_match = simple_pattern.match(line)
            if simple_match and self._valid_description(simple_match.group(1)):
                items.append(
                    ParsedReceiptItem(
                        line_number=index,
                        description=simple_match.group(1).strip(" .:-"),
                        quantity=None,
                        unit_price=None,
                        line_total=abs(parse_indonesian_money(simple_match.group(2))),
                        confidence=Decimal("0.78"),
                    )
                )
        return items

    def _category(self, lines: list[str], items: list[ParsedReceiptItem]) -> ParsedField:
        combined = " ".join([*lines, *(item.description for item in items)]).upper()
        categories = (
            (("BENSIN", "PERTALITE", "SOLAR", "ONGKIR", "KIRIM"), "TRANSPORTATION"),
            (("PLN", "LISTRIK"), "ELECTRICITY"),
            (("INTERNET", "WIFI", "DATA", "PULSA"), "INTERNET"),
            (("IKLAN", "PROMOSI", "BANNER", "ADS"), "PROMOTION"),
            (("KERTAS", "TINTA", "ATK", "ADMIN"), "ADMINISTRATION"),
            (("TEPUNG", "GULA", "MINYAK", "BAHAN", "SAYUR", "DAGING"), "RAW_MATERIALS"),
        )
        for keywords, category in categories:
            if any(keyword in combined for keyword in keywords):
                return ParsedField(category, Decimal("0.84"), "Kata kunci barang/toko")
        return ParsedField("PURCHASES", Decimal("0.65"), "Kategori umum pembelian")

    @staticmethod
    def _money_values(line: str) -> list[tuple[Decimal, str]]:
        values: list[tuple[Decimal, str]] = []
        for match in MONEY_RE.finditer(line.upper()):
            try:
                values.append((parse_indonesian_money(match.group(1)), line))
            except ValueError:
                continue
        return values

    @staticmethod
    def _valid_description(value: str) -> bool:
        cleaned = value.strip(" .:-")
        return len(cleaned) >= 2 and any(character.isalpha() for character in cleaned)
