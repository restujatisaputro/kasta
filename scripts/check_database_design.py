from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = REPOSITORY_ROOT / "documentation/database/kasta-postgresql-v0.1.sql"

EXPECTED_TABLES = {
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "organizations",
    "businesses",
    "business_members",
    "mentors",
    "mentor_business_access",
    "accounts",
    "account_categories",
    "transactions",
    "transaction_items",
    "journal_entries",
    "journal_lines",
    "payment_methods",
    "customers",
    "suppliers",
    "products",
    "stock_movements",
    "receivables",
    "receivable_payments",
    "payables",
    "payable_payments",
    "receipts",
    "receipt_images",
    "ocr_results",
    "ocr_fields",
    "mentor_notes",
    "recommendations",
    "mentoring_sessions",
    "notifications",
    "device_sessions",
    "sync_logs",
    "audit_logs",
}

TENANT_TRANSACTION_TABLES = {
    "transactions",
    "transaction_items",
    "journal_entries",
    "journal_lines",
    "stock_movements",
    "receivables",
    "receivable_payments",
    "payables",
    "payable_payments",
    "receipts",
    "receipt_images",
    "ocr_results",
    "ocr_fields",
    "sync_logs",
}

MONEY_COLUMNS = {
    "products": {"sales_price", "cost_price"},
    "transactions": {"total_amount"},
    "transaction_items": {"unit_price", "discount_amount", "tax_amount", "line_total"},
    "journal_entries": {"total_debit", "total_credit"},
    "journal_lines": {"debit_amount", "credit_amount"},
    "stock_movements": {"unit_cost"},
    "receivables": {"original_amount", "outstanding_amount"},
    "receivable_payments": {"amount"},
    "payables": {"original_amount", "outstanding_amount"},
    "payable_payments": {"amount"},
    "receipts": {"total_amount"},
}


def table_bodies(ddl: str) -> dict[str, str]:
    pattern = re.compile(r"CREATE TABLE kasta\.([a-z_]+) \((.*?)\n\);", re.DOTALL)
    return {name: body for name, body in pattern.findall(ddl)}


def main() -> int:
    ddl = DDL_PATH.read_text(encoding="utf-8")
    tables = table_bodies(ddl)
    errors: list[str] = []

    if set(tables) != EXPECTED_TABLES:
        errors.append(
            f"table mismatch: missing={sorted(EXPECTED_TABLES - set(tables))}, "
            f"extra={sorted(set(tables) - EXPECTED_TABLES)}"
        )

    if re.search(r"\b(?:FLOAT|REAL|DOUBLE\s+PRECISION)\b", ddl, re.IGNORECASE):
        errors.append("floating-point type found in DDL")

    for name, body in tables.items():
        if not re.search(r"\bid UUID PRIMARY KEY DEFAULT gen_random_uuid\(\)", body, re.IGNORECASE):
            errors.append(f"{name}: public UUID primary key/default missing")
        for timestamp in ("created_at", "updated_at"):
            if not re.search(
                rf"\b{timestamp} TIMESTAMPTZ NOT NULL DEFAULT now\(\)", body, re.IGNORECASE
            ):
                errors.append(f"{name}: {timestamp} convention missing")

    for name in TENANT_TRANSACTION_TABLES:
        body = tables.get(name, "")
        if not re.search(
            r"\bbusiness_id UUID NOT NULL REFERENCES kasta\.businesses\(id\)",
            body,
            re.IGNORECASE,
        ):
            errors.append(f"{name}: required business_id tenant FK missing")

    for table, columns in MONEY_COLUMNS.items():
        body = tables.get(table, "")
        for column in columns:
            if not re.search(rf"\b{column}\s+NUMERIC\(18,2\)", body, re.IGNORECASE):
                errors.append(f"{table}.{column}: must use NUMERIC(18,2)")

    if errors:
        print("Rancangan database KASTA tidak valid:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Rancangan database valid: {len(tables)} tabel, "
        f"{sum(len(columns) for columns in MONEY_COLUMNS.values())} kolom uang diperiksa."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
