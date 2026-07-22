from collections import Counter
from decimal import Decimal
from io import BytesIO
from uuid import UUID
from zipfile import ZipFile

import pytest
from sqlalchemy import func, select

from kasta_api.modules.accounting.models import (
    Account,
    FinancialTransaction,
    JournalEntry,
    JournalLine,
)
from kasta_api.modules.inventory.models import Product, StockMovement, TransactionItem
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def inventory_url(environment: AuthTestEnvironment) -> str:
    return f"/api/v1/businesses/{environment.business_a_id}/inventory"


def transaction_url(environment: AuthTestEnvironment) -> str:
    return f"/api/v1/businesses/{environment.business_a_id}/transactions"


def product_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sku": "KOPI-001",
        "barcode": "8991234567890",
        "name": "Kopi Susu Botol",
        "category": "Minuman",
        "unit": "PCS",
        "purchase_price": "8000.00",
        "sale_price": "12000.00",
        "opening_stock": "10.000",
        "minimum_stock": "5.000",
        "is_active": True,
    }
    payload.update(changes)
    return payload


def money_transaction(
    entry_kind: str, product_id: str, quantity: str, unit_price: str
) -> dict[str, object]:
    income = entry_kind == "INCOME"
    return {
        "entry_kind": entry_kind,
        "transaction_date": "2026-07-21",
        "amount": str(Decimal(quantity) * Decimal(unit_price)),
        "category_account": "SALES" if income else "PURCHASES",
        "counterparty_name": "Mitra Uji",
        "payment_method": "CASH",
        "note": "Transaksi produk",
        "items": [
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
            }
        ],
    }


async def create_product(
    environment: AuthTestEnvironment, token: str, **changes: object
) -> dict[str, object]:
    response = await environment.client.post(
        f"{inventory_url(environment)}/products",
        headers=headers(token),
        json=product_payload(**changes),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_product_crud_barcode_low_stock_and_tenant_isolation(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    product = await create_product(auth_environment, tokens.access_token)
    assert product["current_stock"] == "10.000"
    assert product["inventory_value"] == "80000.00"

    duplicate = await auth_environment.client.post(
        f"{inventory_url(auth_environment)}/products",
        headers=headers(tokens.access_token),
        json=product_payload(name="Produk Ganda"),
    )
    assert duplicate.status_code == 409

    scanned = await auth_environment.client.get(
        f"{inventory_url(auth_environment)}/products/by-barcode/8991234567890",
        headers=headers(tokens.access_token),
    )
    assert scanned.status_code == 200
    assert scanned.json()["id"] == product["id"]

    changed = await auth_environment.client.put(
        f"{inventory_url(auth_environment)}/products/{product['id']}",
        headers=headers(tokens.access_token),
        json=product_payload(
            name="Kopi Susu Baru",
            opening_stock="999.000",
            minimum_stock="12.000",
        ),
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["current_stock"] == "10.000"
    assert changed.json()["is_low_stock"] is True

    low = await auth_environment.client.get(
        f"{inventory_url(auth_environment)}/products",
        params={"low_stock": "true"},
        headers=headers(tokens.access_token),
    )
    assert low.status_code == 200
    assert low.json()["total"] == 1

    other_tenant = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_b_id}/inventory/products",
        headers=headers(tokens.access_token),
    )
    assert other_tenant.status_code == 403


async def test_manual_stock_movements_history_and_summary(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    product = await create_product(auth_environment, tokens.access_token)
    product_id = product["id"]
    cases = [
        ("STOCK_IN", "4.000", None, "14.000"),
        ("STOCK_OUT", "2.000", None, "12.000"),
        ("DAMAGED", "1.000", None, "11.000"),
        ("LOST", "1.000", None, "10.000"),
        ("ADJUSTMENT", None, "8.000", "8.000"),
    ]
    for movement_type, quantity, target, expected in cases:
        response = await auth_environment.client.post(
            f"{inventory_url(auth_environment)}/products/{product_id}/movements",
            headers=headers(tokens.access_token),
            json={
                "movement_type": movement_type,
                "quantity": quantity,
                "target_stock": target,
                "reason": f"Pengujian {movement_type}",
                "reference": "TEST-001",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["stock_after"] == expected

    rejected = await auth_environment.client.post(
        f"{inventory_url(auth_environment)}/products/{product_id}/movements",
        headers=headers(tokens.access_token),
        json={
            "movement_type": "STOCK_OUT",
            "quantity": "9.000",
            "reason": "Melebihi stok tersedia",
        },
    )
    assert rejected.status_code == 409

    history = await auth_environment.client.get(
        f"{inventory_url(auth_environment)}/movements",
        params={"product_id": product_id},
        headers=headers(tokens.access_token),
    )
    assert history.status_code == 200
    assert history.json()["total"] == 6

    summary = await auth_environment.client.get(
        f"{inventory_url(auth_environment)}/summary",
        headers=headers(tokens.access_token),
    )
    assert summary.status_code == 200
    assert summary.json()["product_count"] == 1
    assert summary.json()["inventory_value"] == "64000.00"


async def test_sale_purchase_reversal_and_revision_change_stock_atomically(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    product = await create_product(auth_environment, tokens.access_token)
    product_id = product["id"]

    sale = await auth_environment.client.post(
        transaction_url(auth_environment),
        headers=headers(tokens.access_token),
        json=money_transaction("INCOME", product_id, "3.000", "12000.00"),
    )
    assert sale.status_code == 201, sale.text
    sale_id = sale.json()["transaction"]["id"]
    assert await current_stock(auth_environment, UUID(product_id)) == Decimal("7.000")

    revision_payload = money_transaction("INCOME", product_id, "5.000", "12000.00")
    revised = await auth_environment.client.post(
        f"{transaction_url(auth_environment)}/{sale_id}/revision",
        headers=headers(tokens.access_token),
        json={"reason": "Jumlah barang dikoreksi", "replacement": revision_payload},
    )
    assert revised.status_code == 200, revised.text
    replacement_id = revised.json()["transaction"]["id"]
    assert await current_stock(auth_environment, UUID(product_id)) == Decimal("5.000")

    cancelled = await auth_environment.client.post(
        f"{transaction_url(auth_environment)}/{replacement_id}/reversal",
        headers=headers(tokens.access_token),
        json={"reason": "Penjualan dibatalkan"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert await current_stock(auth_environment, UUID(product_id)) == Decimal("10.000")

    purchase = await auth_environment.client.post(
        transaction_url(auth_environment),
        headers=headers(tokens.access_token),
        json=money_transaction("EXPENSE", product_id, "4.000", "9000.00"),
    )
    assert purchase.status_code == 201, purchase.text
    purchase_id = purchase.json()["transaction"]["id"]
    assert await current_stock(auth_environment, UUID(product_id)) == Decimal("14.000")
    async with auth_environment.session_factory() as session:
        purchase_accounts = (
            await session.execute(
                select(Account.system_key, JournalLine.debit_amount, JournalLine.credit_amount)
                .join(JournalLine, JournalLine.account_id == Account.id)
                .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
                .where(JournalEntry.transaction_id == UUID(purchase_id))
            )
        ).all()
    assert set(purchase_accounts) == {
        ("INVENTORY", Decimal("36000.00"), Decimal("0.00")),
        ("CASH", Decimal("0.00"), Decimal("36000.00")),
    }

    purchase_cancelled = await auth_environment.client.post(
        f"{transaction_url(auth_environment)}/{purchase_id}/reversal",
        headers=headers(tokens.access_token),
        json={"reason": "Pembelian dibatalkan"},
    )
    assert purchase_cancelled.status_code == 200, purchase_cancelled.text
    assert await current_stock(auth_environment, UUID(product_id)) == Decimal("10.000")
    async with auth_environment.session_factory() as session:
        restored_price = await session.scalar(
            select(Product.purchase_price).where(Product.id == UUID(product_id))
        )
    assert restored_price == Decimal("8000.00")

    async with auth_environment.session_factory() as session:
        item_count = await session.scalar(select(func.count(TransactionItem.id)))
        movements = (
            await session.scalars(
                select(StockMovement.movement_type).where(
                    StockMovement.product_id == UUID(product_id)
                )
            )
        ).all()
    assert item_count == 6
    assert Counter(movements) == Counter(
        {
            "OPENING": 1,
            "SALE": 1,
            "SALE_REVERSAL": 2,
            "REVISION_ADJUSTMENT": 1,
            "PURCHASE": 1,
            "PURCHASE_REVERSAL": 1,
        }
    )


async def test_insufficient_stock_rolls_back_financial_transaction_and_journal(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    product = await create_product(auth_environment, tokens.access_token, opening_stock="2.000")
    response = await auth_environment.client.post(
        transaction_url(auth_environment),
        headers=headers(tokens.access_token),
        json=money_transaction("INCOME", product["id"], "3.000", "12000.00"),
    )
    assert response.status_code == 409
    assert await current_stock(auth_environment, UUID(product["id"])) == Decimal("2.000")

    async with auth_environment.session_factory() as session:
        transaction_count = await session.scalar(select(func.count(FinancialTransaction.id)))
        journal_count = await session.scalar(select(func.count(JournalEntry.id)))
        item_count = await session.scalar(select(func.count(TransactionItem.id)))
    assert transaction_count == journal_count == item_count == 0


async def test_product_total_must_match_transaction_amount(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    product = await create_product(auth_environment, tokens.access_token)
    payload = money_transaction("INCOME", product["id"], "2.000", "12000.00")
    payload["amount"] = "25000.00"
    response = await auth_environment.client.post(
        transaction_url(auth_environment),
        headers=headers(tokens.access_token),
        json=payload,
    )
    assert response.status_code == 422
    assert await current_stock(auth_environment, UUID(product["id"])) == Decimal("10.000")


async def test_failed_purchase_reversal_keeps_original_transaction_posted(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    product = await create_product(auth_environment, tokens.access_token, opening_stock="0.000")
    purchase = await auth_environment.client.post(
        transaction_url(auth_environment),
        headers=headers(tokens.access_token),
        json=money_transaction("EXPENSE", product["id"], "4.000", "9000.00"),
    )
    assert purchase.status_code == 201, purchase.text
    purchase_id = purchase.json()["transaction"]["id"]

    used = await auth_environment.client.post(
        f"{inventory_url(auth_environment)}/products/{product['id']}/movements",
        headers=headers(tokens.access_token),
        json={
            "movement_type": "STOCK_OUT",
            "quantity": "3.000",
            "reason": "Barang sudah digunakan",
        },
    )
    assert used.status_code == 200

    rejected = await auth_environment.client.post(
        f"{transaction_url(auth_environment)}/{purchase_id}/reversal",
        headers=headers(tokens.access_token),
        json={"reason": "Pembelian hendak dibatalkan"},
    )
    assert rejected.status_code == 409
    assert await current_stock(auth_environment, UUID(product["id"])) == Decimal("1.000")

    async with auth_environment.session_factory() as session:
        original = await session.get(FinancialTransaction, UUID(purchase_id))
        transaction_count = await session.scalar(select(func.count(FinancialTransaction.id)))
        item_count = await session.scalar(select(func.count(TransactionItem.id)))
    assert original is not None
    assert original.status == "POSTED"
    assert original.reversed_by_transaction_id is None
    assert transaction_count == 1
    assert item_count == 1


async def test_csv_import_is_atomic_and_excel_export_is_valid_zip(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    csv_data = (
        "sku,barcode,nama,kategori,satuan,harga_beli,harga_jual,stok_awal,stok_minimum,aktif\n"
        "TEH-001,899000000001,Teh Botol,Minuman,PCS,3000,5000,7,2,ya\n"
        "ROTI-001,899000000002,Roti Isi,Makanan,PCS,4000,6500,5,2,true\n"
    )
    imported = await auth_environment.client.post(
        f"{inventory_url(auth_environment)}/products/import-csv",
        headers=headers(tokens.access_token),
        files={"file": ("produk.csv", csv_data, "text/csv")},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported_count"] == 2

    invalid = csv_data + "TEH-001,,Produk Ganda,Minuman,PCS,1,1,1,1,ya\n"
    rejected = await auth_environment.client.post(
        f"{inventory_url(auth_environment)}/products/import-csv",
        headers=headers(tokens.access_token),
        files={"file": ("produk.csv", invalid, "text/csv")},
    )
    assert rejected.status_code == 409

    listed = await auth_environment.client.get(
        f"{inventory_url(auth_environment)}/products",
        headers=headers(tokens.access_token),
    )
    assert listed.json()["total"] == 2

    exported = await auth_environment.client.get(
        f"{inventory_url(auth_environment)}/products/export.xlsx",
        headers=headers(tokens.access_token),
    )
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    with ZipFile(BytesIO(exported.content)) as workbook:
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()
        sheet = workbook.read("xl/worksheets/sheet1.xml").decode()
    assert "TEH-001" in sheet
    assert "ROTI-001" in sheet


async def current_stock(environment: AuthTestEnvironment, product_id: UUID) -> Decimal:
    async with environment.session_factory() as session:
        stock = await session.scalar(select(Product.current_stock).where(Product.id == product_id))
    assert stock is not None
    return stock
