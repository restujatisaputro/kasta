from enum import StrEnum


class ReportPeriod(StrEnum):
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    QUARTER = "QUARTER"
    YEAR = "YEAR"
    CUSTOM = "CUSTOM"


class ExportFormat(StrEnum):
    PDF = "PDF"
    XLSX = "XLSX"
    CSV = "CSV"
