from enum import StrEnum


class ClosingFrequency(StrEnum):
    """How often the business intends to close its books.

    Purely advisory: it only shapes the *suggested* period end shown to the
    user (see :func:`kasta_api.modules.closing.service.suggested_period_end`).
    Closing itself always accepts any end date up to today, so a business
    that falls behind its own cadence is never blocked from catching up.
    """

    MONTHLY = "MONTHLY"
    SEMIANNUAL = "SEMIANNUAL"
    TRIANNUAL = "TRIANNUAL"
