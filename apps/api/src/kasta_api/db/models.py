"""Import every mapped model so Alembic sees the complete metadata."""

from kasta_api.modules.accounting.models import (
    Account,
    FinancialTransaction,
    JournalEntry,
    JournalLine,
    TransactionRevision,
)
from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.models import (
    AuthDeliveryOutbox,
    AuthOneTimeToken,
    DeviceSession,
    LoginRateLimit,
    Permission,
    Role,
    RolePermission,
)
from kasta_api.modules.businesses.models import (
    Business,
    BusinessCategory,
    BusinessMember,
    BusinessPaymentMethod,
    BusinessProfile,
    OnboardingCompletion,
    Organization,
    OrganizationMember,
)
from kasta_api.modules.inventory.models import Product, StockMovement, TransactionItem
from kasta_api.modules.mentors.models import (
    Mentor,
    MentorBusinessAccess,
    MentoringSession,
    MentorNote,
    Recommendation,
    SupportAccessGrant,
)
from kasta_api.modules.notifications.models import NotificationPreference, PushSubscription
from kasta_api.modules.obligations.models import (
    Customer,
    Notification,
    Payable,
    PayablePayment,
    Receivable,
    ReceivablePayment,
    Supplier,
)
from kasta_api.modules.receipts.models import (
    OcrField,
    OcrResult,
    Receipt,
    ReceiptCorrection,
    ReceiptImage,
    ReceiptItem,
)
from kasta_api.modules.sync.models import (
    DeviceSyncState,
    SyncChange,
    SyncConflictRevision,
    SyncOperationLog,
    SyncRecord,
)
from kasta_api.modules.transactions.models import (
    RecurringTransaction,
    TransactionDraft,
    TransactionSyncLog,
)
from kasta_api.modules.users.models import User

__all__ = [
    "Account",
    "AuditLog",
    "AuthDeliveryOutbox",
    "AuthOneTimeToken",
    "Business",
    "BusinessCategory",
    "BusinessMember",
    "BusinessPaymentMethod",
    "BusinessProfile",
    "Customer",
    "DeviceSession",
    "DeviceSyncState",
    "FinancialTransaction",
    "JournalEntry",
    "JournalLine",
    "LoginRateLimit",
    "Mentor",
    "MentorBusinessAccess",
    "MentorNote",
    "MentoringSession",
    "Notification",
    "NotificationPreference",
    "OcrField",
    "OcrResult",
    "OnboardingCompletion",
    "Organization",
    "OrganizationMember",
    "Payable",
    "PayablePayment",
    "Permission",
    "Product",
    "PushSubscription",
    "Receipt",
    "ReceiptCorrection",
    "ReceiptImage",
    "ReceiptItem",
    "Receivable",
    "ReceivablePayment",
    "Recommendation",
    "RecurringTransaction",
    "Role",
    "RolePermission",
    "StockMovement",
    "Supplier",
    "SupportAccessGrant",
    "SyncChange",
    "SyncConflictRevision",
    "SyncOperationLog",
    "SyncRecord",
    "TransactionDraft",
    "TransactionItem",
    "TransactionRevision",
    "TransactionSyncLog",
    "User",
]
