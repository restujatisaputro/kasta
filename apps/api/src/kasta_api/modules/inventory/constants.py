from enum import StrEnum


class StockMovementType(StrEnum):
    OPENING = "OPENING"
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    DAMAGED = "DAMAGED"
    LOST = "LOST"
    SALE = "SALE"
    PURCHASE = "PURCHASE"
    SALE_REVERSAL = "SALE_REVERSAL"
    PURCHASE_REVERSAL = "PURCHASE_REVERSAL"
    REVISION_ADJUSTMENT = "REVISION_ADJUSTMENT"


class StockDirection(StrEnum):
    IN = "IN"
    OUT = "OUT"


PRODUCT_UNITS = (
    "PCS",
    "BOX",
    "PACK",
    "KG",
    "GRAM",
    "LITER",
    "ML",
    "METER",
    "SET",
    "UNIT",
)
