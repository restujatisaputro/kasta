from enum import StrEnum


class ObligationKind(StrEnum):
    RECEIVABLE = "RECEIVABLE"
    PAYABLE = "PAYABLE"


class ObligationStatus(StrEnum):
    OPEN = "OPEN"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


ACTIVE_STATUSES = {
    ObligationStatus.OPEN.value,
    ObligationStatus.PARTIALLY_PAID.value,
    ObligationStatus.OVERDUE.value,
}
