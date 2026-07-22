from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from kasta_api.modules.accounting.constants import (
    EXPENSE_ACCOUNT_KEYS,
    INCOME_ACCOUNT_KEYS,
    AccountKey,
)
from kasta_api.modules.ocr.constants import ReceiptFieldName, ReceiptImageKind, ReceiptStatus
from kasta_api.modules.ocr.image_processing import hash_distance, preprocess_receipt_image
from kasta_api.modules.ocr.parser import (
    IndonesianReceiptParser,
    ParsedField,
    ParsedReceipt,
    normalize_match,
)
from kasta_api.modules.ocr.repository import ReceiptOcrRepository
from kasta_api.modules.ocr.schemas import (
    DuplicateReceiptResponse,
    OcrFieldResponse,
    ReceiptConfirmRequest,
    ReceiptConfirmResponse,
    ReceiptItemResponse,
    ReceiptReviewResponse,
)
from kasta_api.modules.receipts.models import (
    OcrField,
    OcrResult,
    Receipt,
    ReceiptCorrection,
    ReceiptImage,
    ReceiptItem,
)
from kasta_api.modules.receipts.storage import ReceiptStorage, ValidatedImage
from kasta_api.modules.transactions.constants import EntryKind, PaymentMethod
from kasta_api.modules.transactions.schemas import SimpleTransactionInput
from kasta_api.modules.transactions.service import SimpleTransactionService


class ReceiptOcrService:
    def __init__(
        self,
        repository: ReceiptOcrRepository,
        transaction_service: SimpleTransactionService,
    ) -> None:
        self.repository = repository
        self.transaction_service = transaction_service
        self.parser = IndonesianReceiptParser()

    async def upload_and_process(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        original_upload: UploadFile,
        processed_upload: UploadFile | None,
        raw_ocr: str,
        client_fields_json: str | None,
        storage: ReceiptStorage,
    ) -> ReceiptReviewResponse:
        receipt = Receipt(
            id=uuid4(),
            business_id=business_id,
            status=ReceiptStatus.UPLOADED.value,
            uploaded_by_user_id=actor_user_id,
        )
        self.repository.add(receipt)
        await self.repository.commit()

        started = time.perf_counter()
        receipt.status = ReceiptStatus.PROCESSING.value
        receipt.processing_started_at = datetime.now(UTC)
        await self.repository.commit()
        try:
            original = await storage.validate_upload(original_upload)
            original_key = await storage.upload_scan_image(
                business_id, receipt.id, ReceiptImageKind.ORIGINAL.value, original
            )
            input_for_processing = (
                await storage.validate_upload(processed_upload)
                if processed_upload is not None
                else original
            )
            processed = preprocess_receipt_image(input_for_processing.data)
            processed_image = ValidatedImage(
                data=processed.data,
                content_type=processed.content_type,
                extension="jpg",
                width=processed.width,
                height=processed.height,
            )
            processed_key = await storage.upload_scan_image(
                business_id, receipt.id, ReceiptImageKind.PROCESSED.value, processed_image
            )

            parsed = self.parser.parse(raw_ocr)
            self._merge_client_fields(parsed, client_fields_json)
            duration_ms = round((time.perf_counter() - started) * 1000)
            ocr_result = self._persist_result(
                receipt,
                business_id,
                actor_user_id,
                parsed,
                raw_ocr,
                duration_ms,
                original,
                original_key,
                processed_image,
                processed_key,
                processed.perceptual_hash,
            )
            receipt.perceptual_hash = processed.perceptual_hash
            receipt.merchant_name = parsed.value(ReceiptFieldName.MERCHANT_NAME)
            receipt.merchant_normalized = (
                normalize_match(receipt.merchant_name) if receipt.merchant_name else None
            )
            receipt.receipt_date = self._optional_date(parsed.value(ReceiptFieldName.RECEIPT_DATE))
            receipt.receipt_number = parsed.value(ReceiptFieldName.RECEIPT_NUMBER)
            receipt.total_amount = self._optional_decimal(parsed.value(ReceiptFieldName.TOTAL))
            receipt.processing_completed_at = datetime.now(UTC)
            receipt.processing_duration_ms = duration_ms
            receipt.status = ReceiptStatus.NEEDS_REVIEW.value
            await self.repository.commit()
            await self.repository.refresh(ocr_result)

            duplicates = await self._duplicates(receipt)
            if duplicates:
                receipt.duplicate_of_receipt_id = duplicates[0].id
                await self.repository.commit()
            return await self.review(business_id, receipt.id)
        except Exception as exc:
            await self.repository.rollback()
            failed = await self.repository.get_receipt(business_id, receipt.id)
            if failed is not None:
                failed.status = ReceiptStatus.FAILED.value
                failed.processing_completed_at = datetime.now(UTC)
                failed.processing_duration_ms = round((time.perf_counter() - started) * 1000)
                failed.failure_reason = self._safe_failure(exc)
                await self.repository.commit()
            raise

    async def review(self, business_id: UUID, receipt_id: UUID) -> ReceiptReviewResponse:
        receipt = await self._required_receipt(business_id, receipt_id)
        fields = await self.repository.list_fields(receipt.id)
        items = await self.repository.list_items(receipt.id)
        duplicates = await self._duplicates(receipt)
        return ReceiptReviewResponse(
            id=receipt.id,
            business_id=receipt.business_id,
            status=receipt.status,
            transaction_id=receipt.transaction_id,
            fields=[
                OcrFieldResponse(
                    name=field.field_name,
                    value=(
                        field.corrected_value or ""
                        if field.is_user_corrected
                        else field.field_value
                    ),
                    confidence=field.confidence,
                    source_text=field.source_text,
                    corrected_value=field.corrected_value,
                )
                for field in fields
            ],
            items=[
                ReceiptItemResponse(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                    confidence=item.confidence,
                )
                for item in items
            ],
            duplicate_candidates=duplicates,
            processing_duration_ms=receipt.processing_duration_ms,
            failure_reason=receipt.failure_reason,
            created_at=receipt.created_at,
            updated_at=receipt.updated_at,
        )

    async def confirm(
        self,
        business_id: UUID,
        receipt_id: UUID,
        actor_user_id: UUID,
        payload: ReceiptConfirmRequest,
        *,
        request_id: str | None,
    ) -> ReceiptConfirmResponse:
        receipt = await self._required_receipt(business_id, receipt_id)
        if receipt.status == ReceiptStatus.CONFIRMED.value and receipt.transaction_id is not None:
            return ReceiptConfirmResponse(
                receipt=await self.review(business_id, receipt.id),
                transaction_id=receipt.transaction_id,
            )
        if receipt.status != ReceiptStatus.NEEDS_REVIEW.value:
            raise HTTPException(status_code=409, detail="Nota belum siap untuk dikonfirmasi.")

        duplicates = await self._duplicates(receipt)
        if duplicates and not payload.acknowledge_duplicate:
            raise HTTPException(
                status_code=409,
                detail="Nota mirip dengan catatan sebelumnya. Periksa dan setujui terlebih dahulu.",
            )

        field_map = await self.repository.get_field_map(receipt.id)
        ocr_result = await self.repository.get_result(receipt.id)
        corrections = dict(payload.corrections)
        if payload.entry_kind is not None:
            corrections[ReceiptFieldName.TRANSACTION_KIND.value] = payload.entry_kind.value
        if payload.category_account is not None:
            corrections[ReceiptFieldName.CATEGORY_ACCOUNT.value] = payload.category_account.value
        if payload.payment_method is not None:
            corrections[ReceiptFieldName.PAYMENT_METHOD.value] = payload.payment_method.value
        now = datetime.now(UTC)
        for field_name, new_value in corrections.items():
            field = field_map.get(field_name)
            old_value = field.corrected_value or field.field_value if field is not None else None
            normalized_new = new_value or None
            if old_value == normalized_new:
                continue
            self.repository.add_correction(
                ReceiptCorrection(
                    id=uuid4(),
                    business_id=business_id,
                    receipt_id=receipt.id,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=normalized_new,
                    corrected_by_user_id=actor_user_id,
                    created_at=now,
                )
            )
            if field is not None:
                field.corrected_value = normalized_new
                field.is_user_corrected = True
            elif normalized_new is not None and ocr_result is not None:
                field = OcrField(
                    id=uuid4(),
                    business_id=business_id,
                    receipt_id=receipt.id,
                    ocr_result_id=ocr_result.id,
                    field_name=field_name,
                    field_value=normalized_new,
                    normalized_value=normalize_match(normalized_new),
                    confidence=Decimal("0"),
                    source_text="Input pengguna",
                    is_user_corrected=True,
                    corrected_value=normalized_new,
                )
                self.repository.add(field)
                field_map[field_name] = field

        values = {
            name: corrections.get(
                name,
                field.corrected_value if field.is_user_corrected else field.field_value,
            )
            for name, field in field_map.items()
        }
        values.update({name: value for name, value in corrections.items() if name not in values})
        entry_kind = payload.entry_kind or self._entry_kind(values.get("transaction_kind"))
        category = self._confirmed_category(entry_kind, payload.category_account, values)
        payment = payload.payment_method or self._payment_method(values.get("payment_method"))
        transaction_date = self._required_date(values.get("receipt_date"))
        amount = self._required_total(values.get("total"))
        merchant = values.get("merchant_name") or "Nota usaha"
        note = payload.note or f"Foto nota {merchant}"

        created = await self.transaction_service.create_transaction(
            business_id,
            actor_user_id,
            SimpleTransactionInput(
                entry_kind=entry_kind,
                transaction_date=transaction_date,
                amount=amount,
                category_account=category,
                counterparty_name=merchant,
                payment_method=payment,
                note=note,
                idempotency_key=f"receipt:{receipt.id}",
            ),
            request_id=request_id,
        )
        receipt.transaction_id = created.transaction.id
        receipt.status = ReceiptStatus.CONFIRMED.value
        receipt.verified_by_user_id = actor_user_id
        receipt.confirmed_at = datetime.now(UTC)
        receipt.merchant_name = merchant
        receipt.merchant_normalized = normalize_match(merchant)
        receipt.receipt_date = transaction_date
        receipt.receipt_number = values.get("receipt_number") or None
        receipt.total_amount = amount
        for image in await self.repository.list_images(receipt.id):
            image.transaction_id = created.transaction.id
        await self.repository.commit()
        return ReceiptConfirmResponse(
            receipt=await self.review(business_id, receipt.id),
            transaction_id=created.transaction.id,
        )

    async def image_data(
        self,
        business_id: UUID,
        receipt_id: UUID,
        image_kind: str,
        storage: ReceiptStorage,
    ) -> tuple[bytes, str]:
        await self._required_receipt(business_id, receipt_id)
        images = await self.repository.list_images(receipt_id)
        selected = next((image for image in images if image.image_kind == image_kind), None)
        if selected is None:
            raise HTTPException(status_code=404, detail="Gambar nota tidak ditemukan.")
        return await storage.download(selected.object_key)

    async def image_url(
        self,
        business_id: UUID,
        receipt_id: UUID,
        image_kind: str,
        storage: ReceiptStorage,
    ) -> tuple[str, int]:
        await self._required_receipt(business_id, receipt_id)
        images = await self.repository.list_images(receipt_id)
        selected = next((image for image in images if image.image_kind == image_kind), None)
        if selected is None:
            raise HTTPException(status_code=404, detail="Gambar nota tidak ditemukan.")
        return await storage.presigned_download(selected.object_key)

    def _persist_result(
        self,
        receipt: Receipt,
        business_id: UUID,
        actor_user_id: UUID,
        parsed: ParsedReceipt,
        raw_ocr: str,
        duration_ms: int,
        original: ValidatedImage,
        original_key: str,
        processed: ValidatedImage,
        processed_key: str,
        image_hash: str,
    ) -> OcrResult:
        now = datetime.now(UTC)
        confidences = [field.confidence for field in parsed.fields.values()]
        mean_confidence = (
            sum(confidences, Decimal("0")) / Decimal(len(confidences))
            if confidences
            else Decimal("0")
        )
        result = OcrResult(
            id=uuid4(),
            business_id=business_id,
            receipt_id=receipt.id,
            raw_text=raw_ocr,
            engine="GOOGLE_ML_KIT_TEXT_RECOGNITION",
            engine_version="v2",
            mean_confidence=mean_confidence,
            processing_duration_ms=duration_ms,
            created_at=now,
        )
        records: list[object] = [
            result,
            ReceiptImage(
                id=uuid4(),
                business_id=business_id,
                receipt_id=receipt.id,
                transaction_id=None,
                image_kind=ReceiptImageKind.ORIGINAL.value,
                object_key=original_key,
                content_type=original.content_type,
                size_bytes=len(original.data),
                width=original.width,
                height=original.height,
                perceptual_hash=None,
                uploaded_by_user_id=actor_user_id,
            ),
            ReceiptImage(
                id=uuid4(),
                business_id=business_id,
                receipt_id=receipt.id,
                transaction_id=None,
                image_kind=ReceiptImageKind.PROCESSED.value,
                object_key=processed_key,
                content_type=processed.content_type,
                size_bytes=len(processed.data),
                width=processed.width,
                height=processed.height,
                perceptual_hash=image_hash,
                uploaded_by_user_id=actor_user_id,
            ),
        ]
        records.extend(
            OcrField(
                id=uuid4(),
                business_id=business_id,
                receipt_id=receipt.id,
                ocr_result_id=result.id,
                field_name=str(name),
                field_value=field.value,
                normalized_value=normalize_match(field.value),
                confidence=field.confidence,
                source_text=field.source_text,
            )
            for name, field in parsed.fields.items()
        )
        records.extend(
            ReceiptItem(
                id=uuid4(),
                business_id=business_id,
                receipt_id=receipt.id,
                ocr_result_id=result.id,
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                confidence=item.confidence,
            )
            for item in parsed.items
        )
        self.repository.add_all(records)
        return result

    async def _duplicates(self, receipt: Receipt) -> list[DuplicateReceiptResponse]:
        candidates = await self.repository.duplicate_candidates(
            receipt.business_id,
            receipt.id,
            receipt_date=receipt.receipt_date,
            total=receipt.total_amount,
            merchant_normalized=receipt.merchant_normalized,
            receipt_number=receipt.receipt_number,
        )
        matches: list[DuplicateReceiptResponse] = []
        for candidate in candidates:
            reasons: list[str] = []
            if receipt.receipt_number and candidate.receipt_number == receipt.receipt_number:
                reasons.append("nomor_nota")
            if receipt.receipt_date and candidate.receipt_date == receipt.receipt_date:
                reasons.append("tanggal")
            if receipt.total_amount is not None and candidate.total_amount == receipt.total_amount:
                reasons.append("total")
            if (
                receipt.merchant_normalized
                and candidate.merchant_normalized == receipt.merchant_normalized
            ):
                reasons.append("nama_toko")
            distance = None
            if receipt.perceptual_hash and candidate.perceptual_hash:
                distance = hash_distance(receipt.perceptual_hash, candidate.perceptual_hash)
                if distance <= 6:
                    reasons.append("gambar_mirip")
            strong_number = "nomor_nota" in reasons and len(reasons) >= 2
            strong_image = "gambar_mirip" in reasons and len(reasons) >= 3
            if not (strong_number or strong_image):
                continue
            matches.append(
                DuplicateReceiptResponse(
                    id=candidate.id,
                    merchant_name=candidate.merchant_name,
                    receipt_date=candidate.receipt_date,
                    receipt_number=candidate.receipt_number,
                    total_amount=candidate.total_amount,
                    hash_distance=distance,
                    match_reasons=reasons,
                )
            )
        return matches

    def _merge_client_fields(self, parsed: ParsedReceipt, raw_json: str | None) -> None:
        if not raw_json:
            return
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422, detail="Field OCR dari perangkat tidak valid."
            ) from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="Field OCR dari perangkat tidak valid.")
        for name, raw_field in payload.items():
            if not isinstance(name, str) or not isinstance(raw_field, dict):
                continue
            if name not in {field_name.value for field_name in ReceiptFieldName}:
                continue
            value = raw_field.get("value")
            confidence = raw_field.get("confidence", 0)
            if not isinstance(value, str) or not value.strip():
                continue
            try:
                score = min(Decimal("1"), max(Decimal("0"), Decimal(str(confidence))))
            except InvalidOperation:
                score = Decimal("0")
            current = parsed.fields.get(name)
            if current is None or score > current.confidence:
                parsed.fields[name] = ParsedField(value.strip(), score, "Parser perangkat")

    async def _required_receipt(self, business_id: UUID, receipt_id: UUID) -> Receipt:
        receipt = await self.repository.get_receipt(business_id, receipt_id)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Nota tidak ditemukan.")
        return receipt

    @staticmethod
    def _category_for(entry_kind: EntryKind, values: dict[str, str | None]) -> AccountKey:
        raw = values.get("category_account")
        try:
            candidate = AccountKey(raw) if raw else None
        except ValueError:
            candidate = None
        if entry_kind == EntryKind.INCOME:
            return candidate if candidate in INCOME_ACCOUNT_KEYS else AccountKey.SALES
        return candidate if candidate in EXPENSE_ACCOUNT_KEYS else AccountKey.PURCHASES

    @staticmethod
    def _confirmed_category(
        entry_kind: EntryKind,
        requested: AccountKey | None,
        values: dict[str, str | None],
    ) -> AccountKey:
        if entry_kind == EntryKind.INCOME and requested in INCOME_ACCOUNT_KEYS:
            return requested
        if entry_kind == EntryKind.EXPENSE and requested in EXPENSE_ACCOUNT_KEYS:
            return requested
        return ReceiptOcrService._category_for(entry_kind, values)

    @staticmethod
    def _entry_kind(value: str | None) -> EntryKind:
        try:
            candidate = EntryKind(value or EntryKind.EXPENSE.value)
        except ValueError:
            candidate = EntryKind.EXPENSE
        return (
            candidate if candidate in {EntryKind.INCOME, EntryKind.EXPENSE} else EntryKind.EXPENSE
        )

    @staticmethod
    def _payment_method(value: str | None) -> PaymentMethod:
        try:
            return PaymentMethod(value or PaymentMethod.CASH.value)
        except ValueError:
            return PaymentMethod.CASH

    @staticmethod
    def _required_date(value: str | None) -> date:
        parsed = ReceiptOcrService._optional_date(value)
        if parsed is None:
            raise HTTPException(status_code=422, detail="Periksa tanggal nota.")
        return parsed

    @staticmethod
    def _required_total(value: str | None) -> Decimal:
        parsed = ReceiptOcrService._optional_decimal(value)
        if parsed is None or parsed <= 0:
            raise HTTPException(status_code=422, detail="Periksa total nota.")
        return parsed

    @staticmethod
    def _optional_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _optional_decimal(value: str | None) -> Decimal | None:
        if not value:
            return None
        try:
            return Decimal(value).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None

    @staticmethod
    def _safe_failure(error: Exception) -> str:
        if isinstance(error, HTTPException):
            return str(error.detail)[:500]
        return "Pemrosesan nota gagal. Coba ambil foto dengan pencahayaan lebih baik."
