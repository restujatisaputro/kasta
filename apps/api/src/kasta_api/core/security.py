from __future__ import annotations

import asyncio
import ipaddress
import logging
import struct
from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from kasta_api.core.config import Settings
from kasta_api.core.errors import problem_response

logger = logging.getLogger(__name__)


def client_ip(request: Request, trusted_proxy_cidrs: list[str]) -> str:
    """Return a validated client IP and only trust forwarding headers from known proxies."""

    peer = request.client.host if request.client is not None else "unknown"
    try:
        peer_address = ipaddress.ip_address(peer)
    except ValueError:
        return "unknown"
    trusted = any(
        peer_address in ipaddress.ip_network(network, strict=False)
        for network in trusted_proxy_cidrs
    )
    if not trusted:
        return str(peer_address)
    forwarded = request.headers.get("x-forwarded-for", "").split(",", maxsplit=1)[0].strip()
    try:
        return str(ipaddress.ip_address(forwarded)) if forwarded else str(peer_address)
    except ValueError:
        return str(peer_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, production: bool) -> None:
        super().__init__(app)
        self.production = production

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        response.headers.setdefault("Cache-Control", "no-store")
        if request.url.path in {"/docs", "/redoc"}:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; script-src https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'; "
                "base-uri 'none'",
            )
        else:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        if self.production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Small per-process burst shield; login lockout remains database-backed."""

    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        limit = self._limit_for(request)
        if limit is None:
            return await call_next(request)
        key = f"{client_ip(request, self.settings.trusted_proxy_cidrs)}:{self._bucket(request)}"
        retry_after = await self._consume(key, limit)
        if retry_after is not None:
            return problem_response(
                request,
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Terlalu banyak permintaan. Silakan coba kembali sebentar lagi.",
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    def _limit_for(self, request: Request) -> int | None:
        if request.method == "OPTIONS" or request.url.path.endswith(
            ("/health/live", "/health/ready")
        ):
            return None
        if request.url.path.endswith("/receipt-scans") or request.url.path.endswith("/receipts"):
            return self.settings.upload_rate_limit_per_minute
        if request.url.path.startswith("/api/v1/auth/"):
            return self.settings.sensitive_rate_limit_per_minute
        return self.settings.api_rate_limit_per_minute

    @staticmethod
    def _bucket(request: Request) -> str:
        if request.url.path.startswith("/api/v1/auth/"):
            return "auth"
        if request.url.path.endswith("/receipt-scans") or request.url.path.endswith("/receipts"):
            return "upload"
        return "api"

    async def _consume(self, key: str, limit: int) -> int | None:
        now = monotonic()
        cutoff = now - 60
        async with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return max(1, int(60 - (now - bucket[0])))
            bucket.append(now)
        return None


class MalwareScanner:
    """Minimal ClamAV INSTREAM client with configurable fail-closed behavior."""

    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.malware_scan_enabled
        self.host = settings.malware_scan_host
        self.port = settings.malware_scan_port
        self.timeout = settings.malware_scan_timeout_seconds
        self.fail_closed = settings.malware_scan_fail_closed

    async def scan(self, data: bytes) -> None:
        if not self.enabled:
            return
        try:
            result = await asyncio.wait_for(self._scan_stream(data), timeout=self.timeout)
        except (OSError, TimeoutError) as exc:
            logger.error(
                "Malware scanner unavailable",
                extra={"security_event": "scanner_unavailable"},
            )
            if self.fail_closed:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Pemindaian keamanan berkas sedang tidak tersedia.",
                ) from exc
            return
        if "FOUND" in result:
            logger.warning("Malware upload blocked", extra={"security_event": "malware_blocked"})
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Berkas ditolak oleh pemeriksaan keamanan.",
            )
        if not result.endswith("OK"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Hasil pemindaian keamanan berkas tidak dapat diverifikasi.",
            )

    async def _scan_stream(self, data: bytes) -> str:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            writer.write(b"zINSTREAM\0")
            for offset in range(0, len(data), 64 * 1024):
                chunk = data[offset : offset + 64 * 1024]
                writer.write(struct.pack(">I", len(chunk)))
                writer.write(chunk)
            writer.write(struct.pack(">I", 0))
            await writer.drain()
            response = await reader.read(4096)
            return response.rstrip(b"\0\r\n").decode("utf-8", errors="replace")
        finally:
            writer.close()
            await writer.wait_closed()
