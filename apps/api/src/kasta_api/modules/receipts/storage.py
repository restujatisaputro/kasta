import warnings
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from minio import Minio
from minio.error import S3Error
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from kasta_api.core.config import Settings
from kasta_api.core.security import MalwareScanner

MAX_RECEIPT_BYTES = 8 * 1024 * 1024
MAX_RECEIPT_EDGE = 8192
ALLOWED_FORMATS = {
    "PNG": ("png", "image/png"),
    "JPEG": ("jpg", "image/jpeg"),
    "WEBP": ("webp", "image/webp"),
}


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    data: bytes
    content_type: str
    extension: str
    width: int
    height: int


class ReceiptStorage:
    def __init__(self, settings: Settings) -> None:
        parsed = urlsplit(settings.object_endpoint)
        endpoint = parsed.netloc or parsed.path
        self.bucket = settings.object_bucket_receipts
        self.client = Minio(
            endpoint,
            access_key=settings.object_access_key,
            secret_key=settings.object_secret_key.get_secret_value(),
            secure=settings.object_use_ssl,
        )
        public = urlsplit(settings.object_public_endpoint)
        self.public_client = Minio(
            public.netloc or public.path,
            access_key=settings.object_access_key,
            secret_key=settings.object_secret_key.get_secret_value(),
            secure=public.scheme == "https",
        )
        self.signed_url_seconds = settings.signed_url_seconds
        self.malware_scanner = MalwareScanner(settings)

    async def upload(
        self, business_id: UUID, transaction_id: UUID, upload: UploadFile
    ) -> tuple[str, str, int]:
        image = await self.validate_upload(upload)
        object_key = (
            f"businesses/{business_id}/transactions/{transaction_id}/receipts/"
            f"{uuid4()}.{image.extension}"
        )
        await self.put_bytes(object_key, image.data, image.content_type)
        return object_key, image.content_type, len(image.data)

    async def validate_upload(self, upload: UploadFile) -> ValidatedImage:
        data = await upload.read(MAX_RECEIPT_BYTES + 1)
        await upload.close()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Foto bukti masih kosong.",
            )
        if len(data) > MAX_RECEIPT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Ukuran foto bukti paling besar 8 MB.",
            )
        declared_type = (upload.content_type or "").lower()
        allowed_declared_types = {
            "",
            "application/octet-stream",
            *(content_type for _, content_type in ALLOWED_FORMATS.values()),
        }
        if declared_type not in allowed_declared_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Tipe berkas foto bukti tidak didukung.",
            )
        await self.malware_scanner.scan(data)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    image.verify()
                with Image.open(BytesIO(data)) as image:
                    image_format = image.format
                    width, height = image.size
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Foto bukti harus berupa PNG, JPG, atau WebP yang valid.",
            ) from exc
        if (
            image_format not in ALLOWED_FORMATS
            or width > MAX_RECEIPT_EDGE
            or height > MAX_RECEIPT_EDGE
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Sisi foto bukti paling besar 8192 piksel.",
            )
        extension, content_type = ALLOWED_FORMATS[image_format]
        if declared_type.startswith("image/") and declared_type != content_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Isi berkas tidak sesuai dengan tipe gambar yang dikirim.",
            )
        return ValidatedImage(data, content_type, extension, width, height)

    async def upload_scan_image(
        self,
        business_id: UUID,
        receipt_id: UUID,
        image_kind: str,
        image: ValidatedImage,
    ) -> str:
        object_key = (
            f"businesses/{business_id}/receipt-scans/{receipt_id}/"
            f"{image_kind.lower()}-{uuid4()}.{image.extension}"
        )
        await self.put_bytes(object_key, image.data, image.content_type)
        return object_key

    async def put_bytes(self, object_key: str, data: bytes, content_type: str) -> None:
        try:
            await run_in_threadpool(
                self.client.put_object,
                self.bucket,
                object_key,
                BytesIO(data),
                len(data),
                content_type,
            )
        except S3Error as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Penyimpanan foto bukti sedang tidak tersedia.",
            ) from exc

    async def download(self, object_key: str) -> tuple[bytes, str]:
        try:
            response = await run_in_threadpool(self.client.get_object, self.bucket, object_key)
            try:
                data = await run_in_threadpool(response.read)
                content_type = response.headers.get("content-type", "application/octet-stream")
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Foto bukti tidak ditemukan.",
            ) from exc
        return data, content_type

    async def presigned_download(self, object_key: str) -> tuple[str, int]:
        try:
            url = await run_in_threadpool(
                self.public_client.presigned_get_object,
                self.bucket,
                object_key,
                expires=timedelta(seconds=self.signed_url_seconds),
            )
        except (S3Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Tautan foto bukti tidak dapat dibuat.",
            ) from exc
        return url, self.signed_url_seconds
