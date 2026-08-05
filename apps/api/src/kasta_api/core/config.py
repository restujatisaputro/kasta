import ipaddress
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="KASTA_",
        secrets_dir="/run/secrets" if Path("/run/secrets").is_dir() else None,
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    api_version: Literal["v1"] = "v1"
    database_url: str = "postgresql+psycopg://kasta:kasta-local-only@localhost:5432/kasta"
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [
            AnyHttpUrl("http://localhost:5173"),
            AnyHttpUrl("http://localhost:8080"),
        ]
    )
    cors_allow_credentials: bool = True
    request_id_header: str = "X-Request-ID"
    jwt_signing_key: SecretStr = SecretStr("replace-this-local-development-key")
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "kasta-api"
    jwt_audience: str = "kasta-clients"
    token_hash_key: SecretStr = SecretStr("replace-this-local-token-hash-key")
    outbox_encryption_key: SecretStr = SecretStr("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    access_token_minutes: int = Field(default=15, ge=1, le=1440)
    onboarding_token_minutes: int = Field(default=60, ge=10, le=1440)
    refresh_token_days: int = Field(default=30, ge=1, le=365)
    verification_token_minutes: int = Field(default=30, ge=5, le=1440)
    password_reset_token_minutes: int = Field(default=15, ge=5, le=120)
    mail_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = Field(default=25, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_ssl: bool = False
    smtp_starttls: bool = False
    mail_from: str = "KASTA <noreply@localhost>"
    mail_outbox_poll_seconds: float = Field(default=2.0, ge=0.5, le=60.0)
    mail_outbox_batch_size: int = Field(default=20, ge=1, le=100)
    whatsapp_enabled: bool = False
    whatsapp_api_base_url: AnyHttpUrl = AnyHttpUrl("https://graph.facebook.com")
    whatsapp_graph_api_version: str = "v23.0"
    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: SecretStr | None = None
    whatsapp_template_name: str = "kasta_verification"
    whatsapp_template_language: str = "id"
    login_rate_window_seconds: int = Field(default=300, ge=60, le=3600)
    login_rate_max_attempts: int = Field(default=5, ge=2, le=20)
    login_rate_lock_seconds: int = Field(default=900, ge=60, le=86400)
    account_lock_max_attempts: int = Field(default=10, ge=3, le=50)
    account_lock_seconds: int = Field(default=1800, ge=60, le=86400)
    api_rate_limit_per_minute: int = Field(default=600, ge=10, le=10_000)
    sensitive_rate_limit_per_minute: int = Field(default=300, ge=5, le=1_000)
    upload_rate_limit_per_minute: int = Field(default=20, ge=1, le=1_000)
    trusted_proxy_cidrs: list[str] = Field(default_factory=list)
    object_endpoint: str = "http://localhost:9000"
    object_public_endpoint: str = "http://localhost:9002"
    object_bucket_receipts: str = "kasta-receipts-local"
    object_bucket_business_logos: str = "kasta-business-logos-local"
    object_access_key: str = "kasta"
    object_secret_key: SecretStr = SecretStr("kasta-local-object-storage")
    object_use_ssl: bool = False
    signed_url_seconds: int = Field(default=300, ge=30, le=900)
    malware_scan_enabled: bool = False
    malware_scan_host: str = "clamav"
    malware_scan_port: int = Field(default=3310, ge=1, le=65535)
    malware_scan_timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)
    malware_scan_fail_closed: bool = True
    financial_retention_days: int = Field(default=1825, ge=365, le=3650)
    audit_retention_days: int = Field(default=2555, ge=1825, le=3650)
    security_data_retention_days: int = Field(default=90, ge=30, le=365)

    @property
    def api_prefix(self) -> str:
        return f"/api/{self.api_version}"

    @property
    def cors_origin_strings(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.cors_origins]

    @property
    def expose_api_docs(self) -> bool:
        return self.environment in {"local", "test", "staging"}

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("KASTA_LOG_LEVEL tidak valid")
        return normalized

    @field_validator("trusted_proxy_cidrs")
    @classmethod
    def validate_proxy_cidrs(cls, values: list[str]) -> list[str]:
        for value in values:
            try:
                ipaddress.ip_network(value, strict=False)
            except ValueError as exc:
                raise ValueError(f"Trusted proxy CIDR tidak valid: {value}") from exc
        return values

    @model_validator(mode="after")
    def reject_unsafe_production_settings(self) -> Settings:
        signing_key = self.jwt_signing_key.get_secret_value()
        token_hash_key = self.token_hash_key.get_secret_value()
        outbox_key = self.outbox_encryption_key.get_secret_value()
        object_secret = self.object_secret_key.get_secret_value()
        if self.environment == "production" and (
            self.debug
            or signing_key == "replace-this-local-development-key"
            or token_hash_key == "replace-this-local-token-hash-key"
            or outbox_key == "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
            or object_secret == "kasta-local-object-storage"
        ):
            raise ValueError("Production configuration contains an unsafe development value")
        if self.environment == "production" and (
            len(signing_key) < 32
            or len(token_hash_key) < 32
            or len(object_secret) < 16
            or self.access_token_minutes > 15
            or any(origin.scheme != "https" for origin in self.cors_origins)
            or not self.object_public_endpoint.startswith("https://")
        ):
            raise ValueError("Production configuration does not meet the security baseline")
        if self.cors_allow_credentials and "*" in self.cors_origin_strings:
            raise ValueError("Wildcard CORS tidak boleh digunakan bersama credentials")
        if self.whatsapp_enabled and (
            not self.whatsapp_phone_number_id or self.whatsapp_access_token is None
        ):
            raise ValueError(
                "KASTA_WHATSAPP_PHONE_NUMBER_ID dan KASTA_WHATSAPP_ACCESS_TOKEN wajib diisi "
                "saat KASTA_WHATSAPP_ENABLED aktif"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
