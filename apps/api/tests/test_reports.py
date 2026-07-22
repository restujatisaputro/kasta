from decimal import Decimal
from io import BytesIO
from uuid import UUID
from zipfile import ZipFile

import pytest
from sqlalchemy import update

from kasta_api.modules.accounting.models import FinancialTransaction
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def base(environment: AuthTestEnvironment) -> str:
    return f"/api/v1/businesses/{environment.business_a_id}"


async def seed_report_data(environment: AuthTestEnvironment, token: str) -> dict[str, str]:
    product_response = await environment.client.post(
        f"{base(environment)}/inventory/products",
        headers=headers(token),
        json={
            "sku": "LAP-001",
            "name": "Produk Laporan",
            "category": "Uji",
            "unit": "PCS",
            "purchase_price": "100.00",
            "sale_price": "1000000.00",
            "opening_stock": "10.000",
            "minimum_stock": "2.000",
            "is_active": True,
        },
    )
    assert product_response.status_code == 201, product_response.text
    product_id = product_response.json()["id"]

    transactions = [
        {
            "entry_kind": "INCOME",
            "transaction_date": "2026-07-10",
            "amount": "2000000.00",
            "category_account": "SALES",
            "counterparty_name": "Pelanggan Laporan",
            "payment_method": "CASH",
            "note": "Penjualan produk laporan",
            "items": [{"product_id": product_id, "quantity": "2.000", "unit_price": "1000000.00"}],
        },
        {
            "entry_kind": "EXPENSE",
            "transaction_date": "2026-07-11",
            "amount": "1200000.00",
            "category_account": "RENT",
            "counterparty_name": "Pemilik Ruko",
            "payment_method": "BANK_TRANSFER",
            "note": "Sewa tempat usaha",
        },
        {
            "entry_kind": "CAPITAL",
            "transaction_date": "2026-07-01",
            "amount": "500000.00",
            "payment_method": "CASH",
            "note": "Modal tambahan",
        },
    ]
    ids: list[str] = []
    for payload in transactions:
        response = await environment.client.post(
            f"{base(environment)}/transactions", headers=headers(token), json=payload
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["transaction"]["id"])

    receivable = await environment.client.post(
        f"{base(environment)}/receivables",
        headers=headers(token),
        json={
            "party_name": "Pelanggan Kredit",
            "initial_amount": "300000.00",
            "transaction_date": "2026-07-12",
            "due_date": "2026-08-12",
        },
    )
    payable = await environment.client.post(
        f"{base(environment)}/payables",
        headers=headers(token),
        json={
            "party_name": "Pemasok Kredit",
            "initial_amount": "200000.00",
            "transaction_date": "2026-07-13",
            "due_date": "2026-08-13",
        },
    )
    assert receivable.status_code == payable.status_code == 201
    return {"sale_id": ids[0], "product_id": product_id}


def report_params(**changes: str) -> dict[str, str]:
    params = {
        "period": "CUSTOM",
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
    }
    params.update(changes)
    return params


async def test_financial_report_uses_journal_and_returns_explanations_and_charts(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    seeded = await seed_report_data(auth_environment, tokens.access_token)

    # Deliberately change the transaction header. Journal lines remain the reporting source.
    async with auth_environment.session_factory() as session:
        await session.execute(
            update(FinancialTransaction)
            .where(FinancialTransaction.id == UUID(seeded["sale_id"]))
            .values(amount=Decimal("99999999.00"))
        )
        await session.commit()

    response = await auth_environment.client.get(
        f"{base(auth_environment)}/reports/financial",
        params=report_params(),
        headers=headers(tokens.access_token),
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["context"]["source"] == "JOURNAL"
    assert report["summary"] == {
        "income": "2300000.00",
        "expense": "1400000.00",
        "estimated_profit": "900000.00",
        "cash_in": "2500000.00",
        "cash_out": "1200000.00",
        "net_cash_flow": "1300000.00",
        "receivables": "300000.00",
        "payables": "200000.00",
        "inventory_value": "0.00",
    }
    assert "Usaha memperoleh pemasukan Rp2.300.000" in report["explanation"]
    assert report["profit_loss"]["profit"] == "900000.00"
    assert report["balance_sheet"]["difference"] == "0.00"
    assert report["cash_flow"]["ending_cash_balance"] == "1300000.00"
    assert report["receivables"]["journal_value"] == "300000.00"
    assert report["payables"]["journal_value"] == "200000.00"
    assert report["inventory"]["operational_value"] == "800.00"
    assert report["inventory"]["journal_value"] == "0.00"
    assert report["best_selling_products"][0]["quantity_sold"] == "2.000"
    assert report["best_selling_products"][0]["sales_value"] == "2000000.00"
    assert report["charts"]["income_vs_expense"]
    assert report["charts"]["profit_trend"]
    assert report["charts"]["expense_categories"][0]["label"] in {"Pembelian", "Sewa"}
    assert report["charts"]["daily_sales"]


async def test_report_filters_exports_and_tenant_isolation(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    await seed_report_data(auth_environment, tokens.access_token)
    endpoint = f"{base(auth_environment)}/reports/financial"

    rent = await auth_environment.client.get(
        endpoint,
        params=report_params(category="RENT"),
        headers=headers(tokens.access_token),
    )
    assert rent.status_code == 200
    assert rent.json()["summary"]["income"] == "0.00"
    assert rent.json()["summary"]["expense"] == "1200000.00"

    cash = await auth_environment.client.get(
        endpoint,
        params=report_params(payment_method="CASH"),
        headers=headers(tokens.access_token),
    )
    assert cash.status_code == 200
    assert cash.json()["summary"]["income"] == "2000000.00"
    assert cash.json()["summary"]["cash_in"] == "2500000.00"

    for export_format, signature, content_type in (
        ("PDF", b"%PDF-1.4", "application/pdf"),
        ("XLSX", b"PK", "application/vnd.openxmlformats"),
        ("CSV", b"\xef\xbb\xbf", "text/csv"),
    ):
        exported = await auth_environment.client.get(
            f"{endpoint}/export",
            params={**report_params(), "format": export_format},
            headers=headers(tokens.access_token),
        )
        assert exported.status_code == 200, exported.text
        assert exported.content.startswith(signature)
        assert content_type in exported.headers["content-type"]
        assert "attachment" in exported.headers["content-disposition"]
        if export_format == "XLSX":
            with ZipFile(BytesIO(exported.content)) as workbook:
                assert "xl/worksheets/sheet1.xml" in workbook.namelist()

    invalid_branch = await auth_environment.client.get(
        endpoint,
        params=report_params(branch_id=str(auth_environment.business_b_id)),
        headers=headers(tokens.access_token),
    )
    other_tenant = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_b_id}/reports/financial",
        params=report_params(),
        headers=headers(tokens.access_token),
    )
    assert invalid_branch.status_code == 422
    assert other_tenant.status_code == 403


async def test_custom_period_validation(auth_environment: AuthTestEnvironment) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    response = await auth_environment.client.get(
        f"{base(auth_environment)}/reports/financial",
        params={"period": "CUSTOM", "date_from": "2026-07-31"},
        headers=headers(tokens.access_token),
    )
    assert response.status_code == 422


async def test_reversal_is_netted_from_journal_and_best_sellers(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    seeded = await seed_report_data(auth_environment, tokens.access_token)
    reversal = await auth_environment.client.post(
        f"{base(auth_environment)}/transactions/{seeded['sale_id']}/reversal",
        headers=headers(tokens.access_token),
        json={"reason": "Penjualan dibatalkan", "transaction_date": "2026-07-15"},
    )
    assert reversal.status_code == 200, reversal.text

    response = await auth_environment.client.get(
        f"{base(auth_environment)}/reports/financial",
        params=report_params(),
        headers=headers(tokens.access_token),
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["summary"]["income"] == "300000.00"
    assert report["summary"]["cash_in"] == "2500000.00"
    assert report["summary"]["cash_out"] == "3200000.00"
    assert report["summary"]["net_cash_flow"] == "-700000.00"
    assert report["best_selling_products"] == []
