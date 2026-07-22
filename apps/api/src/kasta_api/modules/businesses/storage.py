from __future__ import annotations

import warnings
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

MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_LOGO_EDGE = 4096
ALLOWED_FORMATS = {
    "PNG": ("png", "image/png"),
    "JPEG": ("jpg", "image/jpeg"),
    "WEBP": ("webp", "image/webp"),
}


class BusinessLogoStorage:
    def __init__(self, settings: Settings) -> None:
        parsed = urlsplit(settings.object_endpoint)
        endpoint = parsed.netloc or parsed.path
        self.bucket = settings.object_bucket_business_logos
        self.client = Minio(
            endpoint,
            access_key=settings.object_access_key,
            secret_key=settings.object_secret_key.get_secret_value(),
            secure=settings.object_use_ssl,
        )
        self.malware_scanner = MalwareScanner(settings)

    async def upload(self, business_id: UUID, upload: UploadFile) -> str:
        data = await upload.read(MAX_LOGO_BYTES + 1)
        await upload.close()
        if len(data) > MAX_LOGO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Ukuran logo paling besar 2 MB.",
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
                detail="Tipe berkas logo tidak didukung.",
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
                detail="Logo harus berupa gambar PNG, JPG, atau WebP yang valid.",
            ) from exc
        if image_format not in ALLOWED_FORMATS or width > MAX_LOGO_EDGE or height > MAX_LOGO_EDGE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Logo harus berupa PNG, JPG, atau WebP dengan sisi paling besar 4096 piksel."
                ),
            )
        extension, content_type = ALLOWED_FORMATS[image_format]
        if declared_type.startswith("image/") and declared_type != content_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Isi berkas tidak sesuai dengan tipe gambar yang dikirim.",
            )
        object_key = f"businesses/{business_id}/profile/logo/{uuid4()}.{extension}"
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
                detail="Penyimpanan logo sedang tidak tersedia.",
            ) from exc
        return object_key

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
                status_code=status.HTTP_404_NOT_FOUND, detail="Logo usaha tidak ditemukan."
            ) from exc
        return data, content_type
