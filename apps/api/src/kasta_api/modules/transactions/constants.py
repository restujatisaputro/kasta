from enum import StrEnum

from kasta_api.modules.accounting.constants import AccountKey


class EntryKind(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    CAPITAL = "CAPITAL"
    OWNER_DRAW = "OWNER_DRAW"


class PaymentMethod(StrEnum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    QRIS = "QRIS"
    E_WALLET = "E_WALLET"
    CARD = "CARD"


class RecurrenceFrequency(StrEnum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


PAYMENT_ACCOUNT = {
    PaymentMethod.CASH: AccountKey.CASH,
    PaymentMethod.BANK_TRANSFER: AccountKey.BANK,
    PaymentMethod.QRIS: AccountKey.DIGITAL_WALLET,
    PaymentMethod.E_WALLET: AccountKey.DIGITAL_WALLET,
    PaymentMethod.CARD: AccountKey.BANK,
}

PAYMENT_LABELS = {
    PaymentMethod.CASH: "Tunai",
    PaymentMethod.BANK_TRANSFER: "Transfer bank",
    PaymentMethod.QRIS: "QRIS",
    PaymentMethod.E_WALLET: "Dompet digital",
    PaymentMethod.CARD: "Kartu",
}

INCOME_LABELS = {
    AccountKey.SALES: "Penjualan",
    AccountKey.SERVICE_REVENUE: "Pendapatan jasa",
    AccountKey.OTHER_REVENUE: "Pendapatan lain",
}

EXPENSE_KEYS = (
    AccountKey.PURCHASES,
    AccountKey.RAW_MATERIALS,
    AccountKey.TRANSPORTATION,
    AccountKey.ELECTRICITY,
    AccountKey.INTERNET,
    AccountKey.SALARY,
    AccountKey.RENT,
    AccountKey.PROMOTION,
    AccountKey.ADMINISTRATION,
    AccountKey.OTHER_EXPENSE,
)
