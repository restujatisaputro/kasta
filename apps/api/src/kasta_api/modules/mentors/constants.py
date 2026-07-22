from enum import StrEnum


class HealthLevel(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class RecommendationStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class SessionStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MentorAccessStatus(StrEnum):
    REQUESTED = "REQUESTED"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class MentorAccessScope(StrEnum):
    SUMMARY = "SUMMARY"
    REPORTS = "REPORTS"
    TRANSACTIONS = "TRANSACTIONS"
    RECEIPTS = "RECEIPTS"
    INVENTORY = "INVENTORY"
    OBLIGATIONS = "OBLIGATIONS"
    EXPORT_REPORTS = "EXPORT_REPORTS"


SCOPE_LABELS: dict[MentorAccessScope, str] = {
    MentorAccessScope.SUMMARY: "Melihat ringkasan",
    MentorAccessScope.REPORTS: "Melihat laporan",
    MentorAccessScope.TRANSACTIONS: "Melihat transaksi",
    MentorAccessScope.RECEIPTS: "Melihat nota",
    MentorAccessScope.INVENTORY: "Melihat stok",
    MentorAccessScope.OBLIGATIONS: "Melihat utang dan piutang",
    MentorAccessScope.EXPORT_REPORTS: "Mengunduh laporan",
}


HEALTH_PRESENTATION = {
    HealthLevel.GREEN: ("Relatif sehat", "✓"),
    HealthLevel.YELLOW: ("Perlu perhatian", "!"),
    HealthLevel.RED: ("Perlu pendampingan", "!!"),
}
