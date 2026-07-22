from enum import StrEnum
from uuid import UUID, uuid5

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")


class RoleCode(StrEnum):
    BUSINESS_OWNER = "business_owner"
    BUSINESS_STAFF = "business_staff"
    MENTOR = "mentor"
    ORGANIZATION_ADMIN = "organization_admin"
    SUPER_ADMIN = "super_admin"


class PermissionCode(StrEnum):
    TRANSACTION_CREATE = "transaction.create"
    TRANSACTION_READ = "transaction.read"
    TRANSACTION_UPDATE = "transaction.update"
    TRANSACTION_DELETE = "transaction.delete"
    TRANSACTION_REVERSE = "transaction.reverse"
    REPORT_READ = "report.read"
    REPORT_EXPORT = "report.export"
    RECEIPT_UPLOAD = "receipt.upload"
    RECEIPT_READ = "receipt.read"
    MENTOR_SUMMARY_READ = "mentor.summary.read"
    MENTOR_TRANSACTION_READ = "mentor.transaction.read"
    MENTOR_NOTE_CREATE = "mentor.note.create"
    MENTOR_RECOMMENDATION_MANAGE = "mentor.recommendation.manage"
    MENTOR_SESSION_MANAGE = "mentor.session.manage"
    MENTOR_REPORT_EXPORT = "mentor.report.export"
    BUSINESS_MEMBER_MANAGE = "business.member.manage"
    SESSION_READ = "session.read"
    SESSION_REVOKE_OWN = "session.revoke.own"
    BUSINESS_PROFILE_READ = "business.profile.read"
    BUSINESS_PROFILE_UPDATE = "business.profile.update"
    PRODUCT_CREATE = "product.create"
    PRODUCT_READ = "product.read"
    PRODUCT_UPDATE = "product.update"
    STOCK_MANAGE = "stock.manage"
    INVENTORY_IMPORT = "inventory.import"
    INVENTORY_EXPORT = "inventory.export"
    RECEIVABLE_CREATE = "receivable.create"
    RECEIVABLE_READ = "receivable.read"
    RECEIVABLE_PAYMENT_CREATE = "receivable.payment.create"
    RECEIVABLE_CANCEL = "receivable.cancel"
    PAYABLE_CREATE = "payable.create"
    PAYABLE_READ = "payable.read"
    PAYABLE_PAYMENT_CREATE = "payable.payment.create"
    PAYABLE_CANCEL = "payable.cancel"
    OBLIGATION_REMINDER_MANAGE = "obligation.reminder.manage"
    NOTIFICATION_READ = "notification.read"
    NOTIFICATION_PREFERENCE_MANAGE = "notification.preference.manage"
    NOTIFICATION_GENERATE = "notification.generate"


ROLE_NAMES: dict[RoleCode, str] = {
    RoleCode.BUSINESS_OWNER: "Pemilik UMKM",
    RoleCode.BUSINESS_STAFF: "Pegawai UMKM",
    RoleCode.MENTOR: "Pembina UMKM",
    RoleCode.ORGANIZATION_ADMIN: "Administrator Organisasi",
    RoleCode.SUPER_ADMIN: "Super Administrator",
}

ROLE_SCOPES: dict[RoleCode, str] = {
    RoleCode.BUSINESS_OWNER: "BUSINESS",
    RoleCode.BUSINESS_STAFF: "BUSINESS",
    RoleCode.MENTOR: "MENTOR",
    RoleCode.ORGANIZATION_ADMIN: "ORGANIZATION",
    RoleCode.SUPER_ADMIN: "PLATFORM",
}

ROLE_PERMISSIONS: dict[RoleCode, frozenset[PermissionCode]] = {
    RoleCode.BUSINESS_OWNER: frozenset(
        {
            PermissionCode.TRANSACTION_CREATE,
            PermissionCode.TRANSACTION_READ,
            PermissionCode.TRANSACTION_UPDATE,
            PermissionCode.TRANSACTION_DELETE,
            PermissionCode.TRANSACTION_REVERSE,
            PermissionCode.REPORT_READ,
            PermissionCode.REPORT_EXPORT,
            PermissionCode.RECEIPT_UPLOAD,
            PermissionCode.RECEIPT_READ,
            PermissionCode.BUSINESS_MEMBER_MANAGE,
            PermissionCode.SESSION_READ,
            PermissionCode.SESSION_REVOKE_OWN,
            PermissionCode.BUSINESS_PROFILE_READ,
            PermissionCode.BUSINESS_PROFILE_UPDATE,
            PermissionCode.PRODUCT_CREATE,
            PermissionCode.PRODUCT_READ,
            PermissionCode.PRODUCT_UPDATE,
            PermissionCode.STOCK_MANAGE,
            PermissionCode.INVENTORY_IMPORT,
            PermissionCode.INVENTORY_EXPORT,
            PermissionCode.RECEIVABLE_CREATE,
            PermissionCode.RECEIVABLE_READ,
            PermissionCode.RECEIVABLE_PAYMENT_CREATE,
            PermissionCode.RECEIVABLE_CANCEL,
            PermissionCode.PAYABLE_CREATE,
            PermissionCode.PAYABLE_READ,
            PermissionCode.PAYABLE_PAYMENT_CREATE,
            PermissionCode.PAYABLE_CANCEL,
            PermissionCode.OBLIGATION_REMINDER_MANAGE,
            PermissionCode.NOTIFICATION_READ,
            PermissionCode.NOTIFICATION_PREFERENCE_MANAGE,
            PermissionCode.NOTIFICATION_GENERATE,
        }
    ),
    RoleCode.BUSINESS_STAFF: frozenset(
        {
            PermissionCode.TRANSACTION_CREATE,
            PermissionCode.TRANSACTION_READ,
            PermissionCode.TRANSACTION_REVERSE,
            PermissionCode.TRANSACTION_UPDATE,
            PermissionCode.REPORT_READ,
            PermissionCode.RECEIPT_UPLOAD,
            PermissionCode.RECEIPT_READ,
            PermissionCode.SESSION_READ,
            PermissionCode.SESSION_REVOKE_OWN,
            PermissionCode.BUSINESS_PROFILE_READ,
            PermissionCode.PRODUCT_CREATE,
            PermissionCode.PRODUCT_READ,
            PermissionCode.PRODUCT_UPDATE,
            PermissionCode.STOCK_MANAGE,
            PermissionCode.RECEIVABLE_CREATE,
            PermissionCode.RECEIVABLE_READ,
            PermissionCode.RECEIVABLE_PAYMENT_CREATE,
            PermissionCode.PAYABLE_CREATE,
            PermissionCode.PAYABLE_READ,
            PermissionCode.PAYABLE_PAYMENT_CREATE,
            PermissionCode.NOTIFICATION_READ,
            PermissionCode.NOTIFICATION_PREFERENCE_MANAGE,
            PermissionCode.NOTIFICATION_GENERATE,
        }
    ),
    RoleCode.MENTOR: frozenset(
        {
            PermissionCode.TRANSACTION_READ,
            PermissionCode.REPORT_READ,
            PermissionCode.REPORT_EXPORT,
            PermissionCode.MENTOR_SUMMARY_READ,
            PermissionCode.MENTOR_TRANSACTION_READ,
            PermissionCode.MENTOR_NOTE_CREATE,
            PermissionCode.MENTOR_RECOMMENDATION_MANAGE,
            PermissionCode.MENTOR_SESSION_MANAGE,
            PermissionCode.MENTOR_REPORT_EXPORT,
            PermissionCode.RECEIPT_READ,
            PermissionCode.SESSION_READ,
            PermissionCode.SESSION_REVOKE_OWN,
            PermissionCode.BUSINESS_PROFILE_READ,
            PermissionCode.PRODUCT_READ,
            PermissionCode.RECEIVABLE_READ,
            PermissionCode.PAYABLE_READ,
            PermissionCode.NOTIFICATION_READ,
            PermissionCode.NOTIFICATION_PREFERENCE_MANAGE,
        }
    ),
    RoleCode.ORGANIZATION_ADMIN: frozenset(
        {
            PermissionCode.TRANSACTION_READ,
            PermissionCode.REPORT_READ,
            PermissionCode.REPORT_EXPORT,
            PermissionCode.RECEIPT_READ,
            PermissionCode.MENTOR_SUMMARY_READ,
            PermissionCode.MENTOR_TRANSACTION_READ,
            PermissionCode.MENTOR_NOTE_CREATE,
            PermissionCode.MENTOR_RECOMMENDATION_MANAGE,
            PermissionCode.MENTOR_SESSION_MANAGE,
            PermissionCode.MENTOR_REPORT_EXPORT,
            PermissionCode.BUSINESS_MEMBER_MANAGE,
            PermissionCode.SESSION_READ,
            PermissionCode.SESSION_REVOKE_OWN,
            PermissionCode.BUSINESS_PROFILE_READ,
            PermissionCode.BUSINESS_PROFILE_UPDATE,
            PermissionCode.PRODUCT_READ,
            PermissionCode.INVENTORY_EXPORT,
            PermissionCode.RECEIVABLE_READ,
            PermissionCode.PAYABLE_READ,
            PermissionCode.NOTIFICATION_READ,
            PermissionCode.NOTIFICATION_PREFERENCE_MANAGE,
        }
    ),
    RoleCode.SUPER_ADMIN: frozenset(PermissionCode),
}


def role_id(code: RoleCode) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"role:{code.value}")


def permission_id(code: PermissionCode) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"permission:{code.value}")
