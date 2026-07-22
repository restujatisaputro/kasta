from enum import StrEnum


class NotificationCategory(StrEnum):
    NO_TRANSACTION_TODAY = "NO_TRANSACTION_TODAY"
    PAYABLE_DUE_SOON = "PAYABLE_DUE_SOON"
    RECEIVABLE_DUE_SOON = "RECEIVABLE_DUE_SOON"
    LOW_STOCK = "LOW_STOCK"
    OCR_NEEDS_REVIEW = "OCR_NEEDS_REVIEW"
    SYNC_FAILED = "SYNC_FAILED"
    MENTOR_ACCESS_REQUEST = "MENTOR_ACCESS_REQUEST"
    NEW_RECOMMENDATION = "NEW_RECOMMENDATION"
    MENTORING_SCHEDULE = "MENTORING_SCHEDULE"
    MONTHLY_REPORT_AVAILABLE = "MONTHLY_REPORT_AVAILABLE"


CATEGORY_LABELS: dict[NotificationCategory, str] = {
    NotificationCategory.NO_TRANSACTION_TODAY: "Belum mencatat transaksi hari ini",
    NotificationCategory.PAYABLE_DUE_SOON: "Utang mendekati jatuh tempo",
    NotificationCategory.RECEIVABLE_DUE_SOON: "Piutang mendekati jatuh tempo",
    NotificationCategory.LOW_STOCK: "Stok minimum",
    NotificationCategory.OCR_NEEDS_REVIEW: "Hasil foto nota perlu diperiksa",
    NotificationCategory.SYNC_FAILED: "Sinkronisasi gagal",
    NotificationCategory.MENTOR_ACCESS_REQUEST: "Permintaan akses pembina",
    NotificationCategory.NEW_RECOMMENDATION: "Rekomendasi baru",
    NotificationCategory.MENTORING_SCHEDULE: "Jadwal pendampingan",
    NotificationCategory.MONTHLY_REPORT_AVAILABLE: "Laporan bulanan tersedia",
}


DEFAULT_ACTION_PATHS: dict[NotificationCategory, str] = {
    NotificationCategory.NO_TRANSACTION_TODAY: "/transaksi",
    NotificationCategory.PAYABLE_DUE_SOON: "/utang",
    NotificationCategory.RECEIVABLE_DUE_SOON: "/piutang",
    NotificationCategory.LOW_STOCK: "/stok",
    NotificationCategory.OCR_NEEDS_REVIEW: "/foto-nota",
    NotificationCategory.SYNC_FAILED: "/sinkronisasi",
    NotificationCategory.MENTOR_ACCESS_REQUEST: "/akses-pembina",
    NotificationCategory.NEW_RECOMMENDATION: "/pembina",
    NotificationCategory.MENTORING_SCHEDULE: "/pembina",
    NotificationCategory.MONTHLY_REPORT_AVAILABLE: "/laporan",
}
