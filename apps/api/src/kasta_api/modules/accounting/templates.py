from dataclasses import dataclass
from uuid import UUID, uuid4

from kasta_api.modules.accounting.constants import (
    AccountKey,
    AccountType,
    NormalBalance,
)
from kasta_api.modules.accounting.models import Account


@dataclass(frozen=True, slots=True)
class AccountTemplate:
    key: AccountKey
    code: str
    name: str
    account_type: AccountType
    normal_balance: NormalBalance


ACCOUNT_TEMPLATES = (
    AccountTemplate(AccountKey.CASH, "1101", "Kas", AccountType.ASSET, NormalBalance.DEBIT),
    AccountTemplate(AccountKey.BANK, "1102", "Bank", AccountType.ASSET, NormalBalance.DEBIT),
    AccountTemplate(
        AccountKey.DIGITAL_WALLET,
        "1103",
        "Dompet Digital",
        AccountType.ASSET,
        NormalBalance.DEBIT,
    ),
    AccountTemplate(
        AccountKey.RECEIVABLE, "1104", "Piutang", AccountType.ASSET, NormalBalance.DEBIT
    ),
    AccountTemplate(
        AccountKey.INVENTORY, "1105", "Persediaan", AccountType.ASSET, NormalBalance.DEBIT
    ),
    AccountTemplate(
        AccountKey.EQUIPMENT, "1106", "Peralatan", AccountType.ASSET, NormalBalance.DEBIT
    ),
    AccountTemplate(
        AccountKey.PAYABLE,
        "2101",
        "Utang Usaha",
        AccountType.LIABILITY,
        NormalBalance.CREDIT,
    ),
    AccountTemplate(
        AccountKey.OTHER_PAYABLE,
        "2102",
        "Utang Lain",
        AccountType.LIABILITY,
        NormalBalance.CREDIT,
    ),
    AccountTemplate(
        AccountKey.OWNER_CAPITAL,
        "3101",
        "Modal Pemilik",
        AccountType.EQUITY,
        NormalBalance.CREDIT,
    ),
    AccountTemplate(
        AccountKey.OWNER_DRAW, "3201", "Prive", AccountType.EQUITY, NormalBalance.DEBIT
    ),
    AccountTemplate(
        AccountKey.RETAINED_EARNINGS,
        "3301",
        "Saldo Laba",
        AccountType.EQUITY,
        NormalBalance.CREDIT,
    ),
    AccountTemplate(
        AccountKey.SALES, "4101", "Penjualan", AccountType.REVENUE, NormalBalance.CREDIT
    ),
    AccountTemplate(
        AccountKey.SERVICE_REVENUE,
        "4201",
        "Pendapatan Jasa",
        AccountType.REVENUE,
        NormalBalance.CREDIT,
    ),
    AccountTemplate(
        AccountKey.OTHER_REVENUE,
        "4301",
        "Pendapatan Lain",
        AccountType.REVENUE,
        NormalBalance.CREDIT,
    ),
    AccountTemplate(
        AccountKey.PURCHASES, "5101", "Pembelian", AccountType.EXPENSE, NormalBalance.DEBIT
    ),
    AccountTemplate(
        AccountKey.RAW_MATERIALS,
        "5201",
        "Bahan Baku",
        AccountType.EXPENSE,
        NormalBalance.DEBIT,
    ),
    AccountTemplate(
        AccountKey.TRANSPORTATION,
        "5301",
        "Transportasi",
        AccountType.EXPENSE,
        NormalBalance.DEBIT,
    ),
    AccountTemplate(
        AccountKey.ELECTRICITY,
        "5401",
        "Listrik",
        AccountType.EXPENSE,
        NormalBalance.DEBIT,
    ),
    AccountTemplate(
        AccountKey.INTERNET, "5501", "Internet", AccountType.EXPENSE, NormalBalance.DEBIT
    ),
    AccountTemplate(AccountKey.SALARY, "5601", "Gaji", AccountType.EXPENSE, NormalBalance.DEBIT),
    AccountTemplate(AccountKey.RENT, "5701", "Sewa", AccountType.EXPENSE, NormalBalance.DEBIT),
    AccountTemplate(
        AccountKey.PROMOTION, "5801", "Promosi", AccountType.EXPENSE, NormalBalance.DEBIT
    ),
    AccountTemplate(
        AccountKey.ADMINISTRATION,
        "5901",
        "Administrasi",
        AccountType.EXPENSE,
        NormalBalance.DEBIT,
    ),
    AccountTemplate(
        AccountKey.OTHER_EXPENSE,
        "5999",
        "Beban Lain",
        AccountType.EXPENSE,
        NormalBalance.DEBIT,
    ),
)

ACCOUNT_TEMPLATE_BY_KEY = {template.key: template for template in ACCOUNT_TEMPLATES}


def create_template_accounts(business_id: UUID) -> list[Account]:
    return [
        Account(
            id=uuid4(),
            business_id=business_id,
            code=template.code,
            name=template.name,
            system_key=template.key.value,
            account_type=template.account_type.value,
            normal_balance=template.normal_balance.value,
            is_system=True,
            is_active=True,
        )
        for template in ACCOUNT_TEMPLATES
    ]
