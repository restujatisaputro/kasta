"""Pemrosesan dan hasil ekstraksi OCR nota."""

from kasta_api.modules.ocr.parser import IndonesianReceiptParser
from kasta_api.modules.ocr.router import router

__all__ = ["IndonesianReceiptParser", "router"]
