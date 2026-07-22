from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from uuid import UUID

from kasta_api.modules.accounting.constants import (
    EXPENSE_ACCOUNT_KEYS,
    INCOME_ACCOUNT_KEYS,
    NON_CASH_ACCOUNT_KEYS,
    OPERATING_PAYMENT_KEYS,
    PURCHASE_TARGET_KEYS,
    AccountKey,
    TransactionType,
)

MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY = Decimal("9999999999999999.99")
ZERO = Decimal("0.00")


class AccountingValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TransactionCommand:
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: date
    description: str
    payment_account: AccountKey | None = None
    category_account: AccountKey | None = None
    idempotency_key: str | None = None
    entry_kind: str | None = None
    counterparty_name: str | None = None
    payment_method_code: str | None = None
    recurring_rule_id: str | None = None
    transaction_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class JournalLineDraft:
    account_key: AccountKey
    debit_amount: Decimal = ZERO
    credit_amount: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class JournalDraft:
    lines: tuple[JournalLineDraft, ...]
    total_debit: Decimal
    total_credit: Decimal


def round_money(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise AccountingValidationError("Jumlah uang harus berupa angka yang valid.")
    try:
        with localcontext() as context:
            context.prec = 28
            rounded = value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise AccountingValidationError("Jumlah uang terlalu besar.") from exc
    if rounded <= ZERO:
        raise AccountingValidationError("Jumlah uang harus lebih besar dari 0.")
    if rounded > MAX_MONEY:
        raise AccountingValidationError("Jumlah uang melebihi batas yang dapat dicatat.")
    return rounded


class JournalEngine:
    def create_draft(self, command: TransactionCommand) -> JournalDraft:
        amount = round_money(command.amount)
        debit_key, credit_key = self.resolve_rule(command)
        draft = JournalDraft(
            lines=(
                JournalLineDraft(account_key=debit_key, debit_amount=amount),
                JournalLineDraft(account_key=credit_key, credit_amount=amount),
            ),
            total_debit=amount,
            total_credit=amount,
        )
        JournalValidator.validate(draft)
        return draft

    @staticmethod
    def resolve_rule(command: TransactionCommand) -> tuple[AccountKey, AccountKey]:
        transaction_type = command.transaction_type
        if transaction_type == TransactionType.CASH_SALE:
            return AccountKey.CASH, JournalEngine._income_target(command)
        if transaction_type == TransactionType.NON_CASH_SALE:
            if command.payment_account not in NON_CASH_ACCOUNT_KEYS:
                raise AccountingValidationError(
                    "Pilih Bank atau Dompet Digital untuk penjualan non-tunai."
                )
            return command.payment_account, JournalEngine._income_target(command)
        if transaction_type == TransactionType.CREDIT_SALE:
            return AccountKey.RECEIVABLE, AccountKey.SALES
        if transaction_type == TransactionType.CASH_PURCHASE:
            payment_account = command.payment_account or AccountKey.CASH
            if payment_account not in OPERATING_PAYMENT_KEYS:
                raise AccountingValidationError("Pilih Kas atau Bank sebagai sumber pembayaran.")
            return JournalEngine._purchase_target(command), payment_account
        if transaction_type == TransactionType.CREDIT_PURCHASE:
            return JournalEngine._purchase_target(command), AccountKey.PAYABLE
        if transaction_type == TransactionType.CAPITAL_CONTRIBUTION:
            return AccountKey.CASH, AccountKey.OWNER_CAPITAL
        if transaction_type == TransactionType.OWNER_DRAW:
            return AccountKey.OWNER_DRAW, AccountKey.CASH
        if transaction_type == TransactionType.PAYABLE_PAYMENT:
            payment_account = command.payment_account or AccountKey.CASH
            if payment_account not in OPERATING_PAYMENT_KEYS:
                raise AccountingValidationError("Pilih Kas atau Bank sebagai sumber pembayaran.")
            return AccountKey.PAYABLE, payment_account
        if transaction_type == TransactionType.RECEIVABLE_RECEIPT:
            payment_account = command.payment_account or AccountKey.CASH
            if payment_account not in OPERATING_PAYMENT_KEYS:
                raise AccountingValidationError("Pilih Kas atau Bank sebagai tempat penerimaan.")
            return payment_account, AccountKey.RECEIVABLE
        if transaction_type == TransactionType.OPERATING_EXPENSE:
            if command.category_account not in EXPENSE_ACCOUNT_KEYS:
                raise AccountingValidationError("Pilih kategori pengeluaran usaha.")
            if command.payment_account not in OPERATING_PAYMENT_KEYS:
                raise AccountingValidationError("Pilih Kas atau Bank sebagai sumber pembayaran.")
            return command.category_account, command.payment_account
        raise AccountingValidationError("Jenis transaksi belum didukung.")

    @staticmethod
    def _purchase_target(command: TransactionCommand) -> AccountKey:
        if command.category_account not in PURCHASE_TARGET_KEYS:
            raise AccountingValidationError("Pilih Persediaan atau kategori pengeluaran.")
        return command.category_account

    @staticmethod
    def _income_target(command: TransactionCommand) -> AccountKey:
        target = command.category_account or AccountKey.SALES
        if target not in INCOME_ACCOUNT_KEYS:
            raise AccountingValidationError("Pilih sumber pemasukan yang tersedia.")
        return target


class JournalValidator:
    @staticmethod
    def validate(draft: JournalDraft) -> None:
        if len(draft.lines) < 2:
            raise AccountingValidationError("Catatan keuangan membutuhkan sedikitnya dua sisi.")
        total_debit = ZERO
        total_credit = ZERO
        for line in draft.lines:
            debit = line.debit_amount
            credit = line.credit_amount
            if debit < ZERO or credit < ZERO:
                raise AccountingValidationError("Nilai catatan tidak boleh negatif.")
            if (debit > ZERO) == (credit > ZERO):
                raise AccountingValidationError(
                    "Setiap baris hanya boleh memiliki satu nilai masuk atau keluar."
                )
            if debit.quantize(MONEY_QUANTUM) != debit or credit.quantize(MONEY_QUANTUM) != credit:
                raise AccountingValidationError("Nilai uang harus menggunakan dua angka desimal.")
            total_debit += debit
            total_credit += credit
        if total_debit <= ZERO or total_debit != total_credit:
            raise AccountingValidationError("Catatan keuangan tidak seimbang.")
        if draft.total_debit != total_debit or draft.total_credit != total_credit:
            raise AccountingValidationError("Jumlah catatan tidak sesuai dengan rinciannya.")
