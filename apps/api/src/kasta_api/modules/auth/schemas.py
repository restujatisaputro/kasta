from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class DeviceInfo(BaseModel):
    device_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=200)
    ]
    platform: Literal["ANDROID", "WEB"]
    device_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = (
        None
    )
    app_version: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = (
        None
    )


class LoginRequest(DeviceInfo):
    business_id: UUID | None = None
    identifier: Identifier
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class RefreshRequest(BaseModel):
    refresh_token: Annotated[str, StringConstraints(min_length=40, max_length=512)]


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class BusinessAccessResponse(BaseModel):
    business_id: UUID
    code: str
    name: str
    role: str


class VerificationRequest(BaseModel):
    identifier: Identifier


class VerificationConfirmRequest(BaseModel):
    token: Annotated[str, StringConstraints(min_length=40, max_length=512)]


class ForgotPasswordRequest(BaseModel):
    identifier: Identifier


class ResetPasswordRequest(BaseModel):
    token: Annotated[str, StringConstraints(min_length=40, max_length=512)]
    new_password: Password


class MessageResponse(BaseModel):
    message: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    platform: str
    device_name: str | None
    app_version: str | None
    last_seen_at: datetime
    expires_at: datetime
    created_at: datetime
    is_current: bool = False


class AuthorizationResponse(BaseModel):
    user_id: UUID
    session_id: UUID
    business_id: UUID
    role: str
    permissions: list[str]


class UserCreate(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=16)
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)
    ]
    password: Password

    @model_validator(mode="after")
    def require_identifier(self) -> UserCreate:
        if self.email is None and self.phone is None:
            raise ValueError("Email atau nomor telepon wajib diisi.")
        return self


class RegistrationRequest(BaseModel):
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)
    ]
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=24)
    password: Password

    @model_validator(mode="after")
    def require_exactly_one_identifier(self) -> RegistrationRequest:
        if (self.email is None) == (self.phone is None):
            raise ValueError("Isi salah satu: email atau nomor telepon.")
        return self


class RegistrationResponse(BaseModel):
    user_id: UUID
    message: str


class OnboardingVerificationResponse(BaseModel):
    onboarding_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
