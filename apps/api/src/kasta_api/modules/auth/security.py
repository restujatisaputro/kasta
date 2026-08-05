from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from email_validator import EmailNotValidError, validate_email
from jwt import InvalidTokenError

from kasta_api.core.config import Settings

PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_identifier(identifier: str) -> tuple[str, str]:
    value = identifier.strip()
    if "@" in value:
        try:
            # ``example.test`` is reserved for the deterministic demo seed. The
            # validator rejects special-use domains unless test mode is enabled,
            # which otherwise makes every documented demo account impossible to
            # authenticate. Keep the exception limited to that exact domain.
            test_environment = value.rpartition("@")[2].lower() == "example.test"
            normalized = validate_email(
                value,
                check_deliverability=False,
                test_environment=test_environment,
            ).normalized.lower()
        except EmailNotValidError as exc:
            raise ValueError("Alamat email tidak valid.") from exc
        return "EMAIL", normalized

    phone = re.sub(r"[\s().-]", "", value)
    if phone.startswith("08"):
        phone = "+62" + phone[1:]
    elif phone.startswith("62"):
        phone = "+" + phone
    if not PHONE_PATTERN.fullmatch(phone):
        raise ValueError("Nomor telepon harus menggunakan format internasional, misalnya +62812...")
    return "PHONE", phone


class PasswordManager:
    def __init__(self, hasher: PasswordHasher | None = None) -> None:
        self._hasher = hasher or PasswordHasher(
            time_cost=3,
            memory_cost=65_536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self._dummy_hash = self._hasher.hash(secrets.token_urlsafe(32))

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, stored_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(stored_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def verify_dummy(self, password: str) -> None:
        self.verify(self._dummy_hash, password)

    def needs_rehash(self, stored_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(stored_hash)
        except InvalidHashError:
            return True


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: UUID
    session_id: UUID
    business_id: UUID | None
    token_id: UUID
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class OnboardingTokenClaims:
    user_id: UUID
    token_id: UUID
    expires_at: datetime


class TokenManager:
    def __init__(self, settings: Settings) -> None:
        self._signing_key = settings.jwt_signing_key.get_secret_value()
        self._hash_key = settings.token_hash_key.get_secret_value().encode()
        self._algorithm = settings.jwt_algorithm
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience
        self._access_minutes = settings.access_token_minutes

    @property
    def access_token_seconds(self) -> int:
        return self._access_minutes * 60

    def create_access_token(
        self, user_id: UUID, session_id: UUID, business_id: UUID | None = None
    ) -> str:
        now = utc_now()
        payload: dict[str, Any] = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": str(user_id),
            "sid": str(session_id),
            "jti": str(uuid4()),
            "typ": "access",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=self._access_minutes),
        }
        if business_id is not None:
            payload["bid"] = str(business_id)
        return jwt.encode(payload, self._signing_key, algorithm=self._algorithm)

    def create_onboarding_token(self, user_id: UUID, lifetime_minutes: int) -> str:
        now = utc_now()
        payload: dict[str, Any] = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": str(user_id),
            "jti": str(uuid4()),
            "typ": "onboarding",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=lifetime_minutes),
        }
        return jwt.encode(payload, self._signing_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._signing_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "require": ["iss", "aud", "sub", "sid", "jti", "typ", "exp", "iat"]
                },
            )
            if payload["typ"] != "access":
                raise InvalidTokenError("unexpected token type")
            expires_at = datetime.fromtimestamp(float(payload["exp"]), tz=UTC)
            return AccessTokenClaims(
                user_id=UUID(str(payload["sub"])),
                session_id=UUID(str(payload["sid"])),
                business_id=UUID(str(payload["bid"])) if payload.get("bid") else None,
                token_id=UUID(str(payload["jti"])),
                expires_at=expires_at,
            )
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise ValueError("Token akses tidak valid atau sudah kedaluwarsa.") from exc

    def decode_onboarding_token(self, token: str) -> OnboardingTokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._signing_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["iss", "aud", "sub", "jti", "typ", "exp", "iat"]},
            )
            if payload["typ"] != "onboarding":
                raise InvalidTokenError("unexpected token type")
            return OnboardingTokenClaims(
                user_id=UUID(str(payload["sub"])),
                token_id=UUID(str(payload["jti"])),
                expires_at=datetime.fromtimestamp(float(payload["exp"]), tz=UTC),
            )
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise ValueError("Token onboarding tidak valid atau sudah kedaluwarsa.") from exc

    def create_opaque_token(self, reference_id: UUID) -> tuple[str, str]:
        secret = secrets.token_urlsafe(48)
        return f"{reference_id}.{secret}", self.hash_value(secret)

    def parse_opaque_token(self, token: str) -> tuple[UUID, str]:
        reference, separator, secret = token.partition(".")
        if not separator or not secret:
            raise ValueError("Token tidak valid.")
        try:
            reference_id = UUID(reference)
        except ValueError as exc:
            raise ValueError("Token tidak valid.") from exc
        return reference_id, secret

    def hash_value(self, value: str) -> str:
        return hmac.new(self._hash_key, value.encode(), hashlib.sha256).hexdigest()

    def matches_hash(self, value: str, expected_hash: str) -> bool:
        return hmac.compare_digest(self.hash_value(value), expected_hash)


class OutboxCipher:
    def __init__(self, settings: Settings) -> None:
        try:
            key = base64.urlsafe_b64decode(settings.outbox_encryption_key.get_secret_value())
        except (ValueError, TypeError) as exc:
            raise ValueError("KASTA_OUTBOX_ENCRYPTION_KEY harus berupa base64 URL-safe.") from exc
        if len(key) != 32:
            raise ValueError("KASTA_OUTBOX_ENCRYPTION_KEY harus berisi tepat 32 byte.")
        self._cipher = AESGCM(key)

    def encrypt(self, payload: dict[str, str]) -> tuple[bytes, bytes]:
        nonce = os.urandom(12)
        plaintext = json.dumps(payload, separators=(",", ":")).encode()
        return nonce, self._cipher.encrypt(nonce, plaintext, None)

    def decrypt(self, nonce: bytes, ciphertext: bytes) -> dict[str, str]:
        decoded = json.loads(self._cipher.decrypt(nonce, ciphertext, None))
        if not isinstance(decoded, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in decoded.items()
        ):
            raise ValueError("Payload outbox tidak valid.")
        return decoded
