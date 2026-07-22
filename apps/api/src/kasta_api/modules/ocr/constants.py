from enum import StrEnum


class ReceiptStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class ReceiptImageKind(StrEnum):
    ORIGINAL = "ORIGINAL"
    PROCESSED = "PROCESSED"
    TRANSACTION_ATTACHMENT = "TRANSACTION_ATTACHMENT"


class ReceiptFieldName(StrEnum):
    MERCHANT_NAME = "merchant_name"
    RECEIPT_DATE = "receipt_date"
    RECEIPT_NUMBER = "receipt_number"
    SUBTOTAL = "subtotal"
    DISCOUNT = "discount"
    TAX = "tax"
    TOTAL = "total"
    PAYMENT_METHOD = "payment_method"
    TRANSACTION_KIND = "transaction_kind"
    CATEGORY_ACCOUNT = "category_account"
