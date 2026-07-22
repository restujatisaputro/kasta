from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from kasta_api.core.config import Settings
from kasta_api.modules.auth.models import (
    AuthDeliveryOutbox,
    AuthOneTimeToken,
    DeviceSession,
    LoginRateLimit,
)
from kasta_api.modules.auth.repository import AuthorizationRecord, AuthRepository
from kasta_api.modules.auth.schemas import LoginRequest, RegistrationRequest, TokenPairResponse
from kasta_api.modules.auth.security import (
    OutboxCipher,
    PasswordManager,
    TokenManager,
    normalize_identifier,
    utc_now,
)
from kasta_api.modules.users.models import User

INVALID_CREDENTIALS = "Email/nomor telepon atau password tidak sesuai."
INVALID_TOKEN = "Token tidak valid atau sudah kedaluwarsa."
GENERIC_VERIFICATION_MESSAGE = (
    "Jika akun ditemukan dan belum terverifikasi, petunjuk verifikasi akan dikirim."
)
GENERIC_RESET_MESSAGE = "Jika akun ditemukan, petunjuk pengaturan ulang password akan dikirim."
logger = logging.getLogger(__name__)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        settings: Settings,
        password_manager: PasswordManager,
        token_manager: TokenManager,
        outbox_cipher: OutboxCipher,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.password_manager = password_manager
        self.token_manager = token_manager
        self.outbox_cipher = outbox_cipher

    async def register_account(self, request: RegistrationRequest) -> UUID:
        raw_identifier = request.email if request.email is not None else request.phone
        if raw_identifier is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Email atau nomor telepon wajib diisi.",
            )
        try:
            kind, identifier = normalize_identifier(raw_identifier)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
        if await self.repository.get_user_by_identifier(kind, identifier) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email atau nomor telepon sudah digunakan.",
            )
        user = User(
            email=identifier if kind == "EMAIL" else None,
            phone=identifier if kind == "PHONE" else None,
            full_name=request.full_name,
            password_hash=self.password_manager.hash(request.password),
            status="ACTIVE",
        )
        await self.repository.add_user(user)
        await self._issue_one_time_token(
            user_id=user.id,
            purpose=f"VERIFY_{kind}",
            target=identifier,
            channel=kind,
            lifetime=timedelta(minutes=self.settings.verification_token_minutes),
        )
        logger.info(
            "Onboarding account created",
            extra={"security_event": "account_registered", "user_id": str(user.id)},
        )
        return user.id

    async def login(
        self,
        request: LoginRequest,
        *,
        ip_address: str,
        user_agent: str | None,
    ) -> TokenPairResponse:
        try:
            identifier_kind, identifier = normalize_identifier(request.identifier)
        except ValueError:
            identifier_kind, identifier = "INVALID", request.identifier.strip().lower()

        rate_key = self.token_manager.hash_value(f"login:{identifier}:{ip_address}")
        await self._enforce_rate_limit(rate_key)

        user = (
            await self.repository.get_user_by_identifier(identifier_kind, identifier, lock=True)
            if identifier_kind != "INVALID"
            else None
        )
        now = utc_now()
        if user is not None and user.locked_until is not None:
            remaining = int((_as_utc(user.locked_until) - now).total_seconds())
            if remaining > 0:
                self.password_manager.verify_dummy(request.password)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Akun dikunci sementara karena terlalu banyak percobaan login.",
                    headers={"Retry-After": str(max(remaining, 1))},
                )
            user.locked_until = None
            user.failed_login_attempts = 0
        password_valid = False
        if user is None:
            self.password_manager.verify_dummy(request.password)
        else:
            password_valid = self.password_manager.verify(user.password_hash, request.password)

        if user is None or not password_valid or user.status != "ACTIVE":
            account_blocked_for = self._record_failed_account_login(user, now)
            blocked_for = await self._record_failed_login(rate_key)
            await self.repository.commit()
            logger.warning(
                "Login rejected",
                extra={
                    "security_event": "login_failed",
                    "business_id": str(request.business_id),
                },
            )
            effective_block = account_blocked_for or blocked_for
            if effective_block is not None:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Terlalu banyak percobaan login. Silakan coba lagi nanti.",
                    headers={"Retry-After": str(effective_block)},
                )
            raise self._authentication_error(INVALID_CREDENTIALS)

        if identifier_kind == "EMAIL" and user.email_verified_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Email belum diverifikasi."
            )
        if identifier_kind == "PHONE" and user.phone_verified_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nomor telepon belum diverifikasi.",
            )

        authorization = await self.repository.resolve_authorization(user.id, request.business_id)
        if authorization is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses aktif ke usaha ini.",
            )

        await self.repository.clear_rate_limit(rate_key)
        user.failed_login_attempts = 0
        user.locked_until = None
        if self.password_manager.needs_rehash(user.password_hash):
            user.password_hash = self.password_manager.hash(request.password)
        user.last_login_at = now

        session_id = uuid4()
        refresh_token, refresh_hash = self.token_manager.create_opaque_token(session_id)
        device_session = DeviceSession(
            id=session_id,
            user_id=user.id,
            business_id=request.business_id,
            token_family_id=uuid4(),
            refresh_token_hash=refresh_hash,
            device_identifier_hash=self.token_manager.hash_value(request.device_id),
            platform=request.platform,
            device_name=request.device_name,
            app_version=request.app_version,
            user_agent=user_agent,
            ip_address_hash=self.token_manager.hash_value(ip_address),
            last_seen_at=now,
            expires_at=now + timedelta(days=self.settings.refresh_token_days),
        )
        await self.repository.add_device_session(device_session)
        await self.repository.commit()
        logger.info(
            "Login succeeded",
            extra={
                "security_event": "login_succeeded",
                "user_id": str(user.id),
                "business_id": str(request.business_id),
                "session_id": str(device_session.id),
            },
        )
        return self._token_pair(user.id, request.business_id, device_session.id, refresh_token)

    async def refresh(
        self, refresh_token: str, *, ip_address: str, user_agent: str | None
    ) -> TokenPairResponse:
        try:
            session_id, secret = self.token_manager.parse_opaque_token(refresh_token)
        except ValueError as exc:
            raise self._authentication_error(INVALID_TOKEN) from exc

        device_session = await self.repository.get_device_session(session_id, lock=True)
        now = utc_now()
        if device_session is None:
            raise self._authentication_error(INVALID_TOKEN)
        if device_session.revoked_at is not None or _as_utc(device_session.expires_at) <= now:
            if device_session.revoked_at is None:
                device_session.revoked_at = now
                device_session.revocation_reason = "EXPIRED"
                await self.repository.commit()
            raise self._authentication_error(INVALID_TOKEN)
        if not self.token_manager.matches_hash(secret, device_session.refresh_token_hash):
            device_session.revoked_at = now
            device_session.revocation_reason = "REFRESH_REUSE_DETECTED"
            await self.repository.commit()
            logger.warning(
                "Refresh token reuse detected; session revoked",
                extra={
                    "security_event": "refresh_reuse_detected",
                    "user_id": str(device_session.user_id),
                    "business_id": str(device_session.business_id),
                    "session_id": str(device_session.id),
                },
            )
            raise self._authentication_error(INVALID_TOKEN)

        authorization = await self.repository.resolve_authorization(
            device_session.user_id, device_session.business_id
        )
        if authorization is None:
            device_session.revoked_at = now
            device_session.revocation_reason = "ACCESS_REMOVED"
            await self.repository.commit()
            raise self._authentication_error(INVALID_TOKEN)

        rotated_token, rotated_hash = self.token_manager.create_opaque_token(device_session.id)
        device_session.refresh_token_hash = rotated_hash
        device_session.rotation_counter += 1
        device_session.last_seen_at = now
        device_session.ip_address_hash = self.token_manager.hash_value(ip_address)
        device_session.user_agent = user_agent
        await self.repository.commit()
        logger.info(
            "Refresh token rotated",
            extra={
                "security_event": "refresh_rotated",
                "user_id": str(device_session.user_id),
                "business_id": str(device_session.business_id),
                "session_id": str(device_session.id),
            },
        )
        return self._token_pair(
            device_session.user_id,
            device_session.business_id,
            device_session.id,
            rotated_token,
        )

    async def request_verification(self, identifier_value: str) -> str:
        try:
            kind, identifier = normalize_identifier(identifier_value)
        except ValueError:
            return GENERIC_VERIFICATION_MESSAGE
        user = await self.repository.get_user_by_identifier(kind, identifier)
        if user is None:
            return GENERIC_VERIFICATION_MESSAGE
        if (kind == "EMAIL" and user.email_verified_at is not None) or (
            kind == "PHONE" and user.phone_verified_at is not None
        ):
            return GENERIC_VERIFICATION_MESSAGE

        purpose = f"VERIFY_{kind}"
        await self._issue_one_time_token(
            user_id=user.id,
            purpose=purpose,
            target=identifier,
            channel=kind,
            lifetime=timedelta(minutes=self.settings.verification_token_minutes),
        )
        return GENERIC_VERIFICATION_MESSAGE

    async def confirm_verification(self, raw_token: str) -> User:
        token, _ = await self._validated_one_time_token(raw_token, {"VERIFY_EMAIL", "VERIFY_PHONE"})
        user = await self.repository.get_user(token.user_id)
        if user is None or user.deleted_at is not None:
            raise self._authentication_error(INVALID_TOKEN)
        now = utc_now()
        if token.purpose == "VERIFY_EMAIL":
            if user.email != token.target:
                raise self._authentication_error(INVALID_TOKEN)
            user.email_verified_at = now
        else:
            if user.phone != token.target:
                raise self._authentication_error(INVALID_TOKEN)
            user.phone_verified_at = now
        token.consumed_at = now
        await self.repository.commit()
        return user

    async def forgot_password(self, identifier_value: str) -> str:
        try:
            kind, identifier = normalize_identifier(identifier_value)
        except ValueError:
            return GENERIC_RESET_MESSAGE
        user = await self.repository.get_user_by_identifier(kind, identifier)
        if user is None or user.status != "ACTIVE":
            return GENERIC_RESET_MESSAGE
        await self._issue_one_time_token(
            user_id=user.id,
            purpose="RESET_PASSWORD",
            target=identifier,
            channel=kind,
            lifetime=timedelta(minutes=self.settings.password_reset_token_minutes),
        )
        return GENERIC_RESET_MESSAGE

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        token, _ = await self._validated_one_time_token(raw_token, {"RESET_PASSWORD"})
        user = await self.repository.get_user(token.user_id)
        if user is None or user.deleted_at is not None or user.status != "ACTIVE":
            raise self._authentication_error(INVALID_TOKEN)
        now = utc_now()
        user.password_hash = self.password_manager.hash(new_password)
        user.password_changed_at = now
        token.consumed_at = now
        await self.repository.revoke_user_sessions(user.id, now, "PASSWORD_RESET")
        await self.repository.commit()
        logger.info(
            "Password reset completed and sessions revoked",
            extra={"security_event": "password_reset", "user_id": str(user.id)},
        )

    async def list_sessions(
        self, user_id: UUID, business_id: UUID, current_session_id: UUID
    ) -> list[tuple[DeviceSession, bool]]:
        now = utc_now()
        sessions = await self.repository.list_user_sessions(user_id, business_id)
        return [
            (device_session, device_session.id == current_session_id)
            for device_session in sessions
            if _as_utc(device_session.expires_at) > now
        ]

    async def logout_device(self, user_id: UUID, business_id: UUID, session_id: UUID) -> None:
        device_session = await self.repository.get_device_session(session_id, lock=True)
        if (
            device_session is None
            or device_session.user_id != user_id
            or device_session.business_id != business_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sesi tidak ditemukan."
            )
        if device_session.revoked_at is None:
            device_session.revoked_at = utc_now()
            device_session.revocation_reason = "USER_LOGOUT"
            await self.repository.commit()
            logger.info(
                "Device session revoked",
                extra={
                    "security_event": "device_logout",
                    "user_id": str(user_id),
                    "business_id": str(business_id),
                    "session_id": str(session_id),
                },
            )

    async def logout_all(self, user_id: UUID, business_id: UUID) -> int:
        count = await self.repository.revoke_user_sessions(
            user_id, utc_now(), "USER_LOGOUT_ALL", business_id
        )
        await self.repository.commit()
        logger.info(
            "All business device sessions revoked",
            extra={
                "security_event": "all_devices_logout",
                "user_id": str(user_id),
                "business_id": str(business_id),
            },
        )
        return count

    async def _issue_one_time_token(
        self,
        *,
        user_id: UUID,
        purpose: str,
        target: str,
        channel: str,
        lifetime: timedelta,
    ) -> None:
        now = utc_now()
        token_id = uuid4()
        raw_token, token_hash = self.token_manager.create_opaque_token(token_id)
        await self.repository.consume_previous_tokens(user_id, purpose, now)
        token = AuthOneTimeToken(
            id=token_id,
            user_id=user_id,
            purpose=purpose,
            target=target,
            token_hash=token_hash,
            expires_at=now + lifetime,
        )
        await self.repository.add_one_time_token(token)
        nonce, ciphertext = self.outbox_cipher.encrypt(
            {"token": raw_token, "purpose": purpose, "destination": target}
        )
        await self.repository.add_outbox_message(
            AuthDeliveryOutbox(
                user_id=user_id,
                channel=channel,
                destination=target,
                template=purpose.lower(),
                payload_nonce=nonce,
                payload_ciphertext=ciphertext,
            )
        )
        await self.repository.commit()

    async def _validated_one_time_token(
        self, raw_token: str, allowed_purposes: set[str]
    ) -> tuple[AuthOneTimeToken, str]:
        try:
            token_id, secret = self.token_manager.parse_opaque_token(raw_token)
        except ValueError as exc:
            raise self._authentication_error(INVALID_TOKEN) from exc
        token = await self.repository.get_one_time_token(token_id, lock=True)
        if (
            token is None
            or token.purpose not in allowed_purposes
            or token.consumed_at is not None
            or _as_utc(token.expires_at) <= utc_now()
            or not self.token_manager.matches_hash(secret, token.token_hash)
        ):
            raise self._authentication_error(INVALID_TOKEN)
        return token, secret

    async def _enforce_rate_limit(self, key_hash: str) -> None:
        rate_limit = await self.repository.get_rate_limit(key_hash, lock=True)
        if rate_limit is None or rate_limit.blocked_until is None:
            return
        remaining = int((_as_utc(rate_limit.blocked_until) - utc_now()).total_seconds())
        if remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Terlalu banyak percobaan login. Silakan coba lagi nanti.",
                headers={"Retry-After": str(max(remaining, 1))},
            )

    async def _record_failed_login(self, key_hash: str) -> int | None:
        now = utc_now()
        rate_limit = await self.repository.get_rate_limit(key_hash, lock=True)
        window = timedelta(seconds=self.settings.login_rate_window_seconds)
        if rate_limit is None:
            rate_limit = LoginRateLimit(
                key_hash=key_hash,
                attempt_count=1,
                window_started_at=now,
            )
            self.repository.add_rate_limit(rate_limit)
        elif now - _as_utc(rate_limit.window_started_at) >= window:
            rate_limit.attempt_count = 1
            rate_limit.window_started_at = now
            rate_limit.blocked_until = None
        else:
            rate_limit.attempt_count += 1

        if rate_limit.attempt_count >= self.settings.login_rate_max_attempts:
            rate_limit.blocked_until = now + timedelta(
                seconds=self.settings.login_rate_lock_seconds
            )
            return self.settings.login_rate_lock_seconds
        return None

    def _record_failed_account_login(self, user: User | None, now: datetime) -> int | None:
        if user is None or user.status != "ACTIVE":
            return None
        user.failed_login_attempts += 1
        if user.failed_login_attempts < self.settings.account_lock_max_attempts:
            return None
        user.locked_until = now + timedelta(seconds=self.settings.account_lock_seconds)
        logger.warning(
            "Account temporarily locked",
            extra={"security_event": "account_locked", "user_id": str(user.id)},
        )
        return self.settings.account_lock_seconds

    def _token_pair(
        self, user_id: UUID, business_id: UUID, session_id: UUID, refresh_token: str
    ) -> TokenPairResponse:
        return TokenPairResponse(
            access_token=self.token_manager.create_access_token(user_id, session_id, business_id),
            refresh_token=refresh_token,
            expires_in=self.token_manager.access_token_seconds,
        )

    @staticmethod
    def _authentication_error(detail: str) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def permission_denied(permission: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Izin '{permission}' diperlukan untuk tindakan ini.",
    )


def assert_permission(authorization: AuthorizationRecord, permission: str) -> None:
    if permission not in authorization.permissions:
        raise permission_denied(permission)
