"""Authentication request and response schemas."""
import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator

OTP_PURPOSES = {"login", "register", "reset_password", "bind_identity", "change_phone"}


def _validate_phone(value: Optional[str]) -> Optional[str]:
    if value is not None and not re.match(r"^1[3-9]\d{9}$", value):
        raise ValueError("phone format is invalid")
    return value


def _validate_code(value: str) -> str:
    if not re.match(r"^\d{6}$", value):
        raise ValueError("code must be 6 digits")
    return value


class _IdentityRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    account: Optional[str] = None

    @property
    def identity_account(self) -> str:
        return self.account or self.phone or self.email or ""

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        return _validate_phone(value)

    @model_validator(mode="after")
    def validate_identity(self):
        if not self.identity_account:
            raise ValueError("account is required")
        return self


class SendCodeRequest(_IdentityRequest):
    purpose: str = "login"

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, value: str) -> str:
        if value not in OTP_PURPOSES:
            raise ValueError("purpose is invalid")
        return value


class LoginByPhoneRequest(_IdentityRequest):
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _validate_code(value)


class LoginByPasswordRequest(_IdentityRequest):
    password: str


class RegisterByPhoneRequest(_IdentityRequest):
    code: str
    password: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _validate_code(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 50:
            raise ValueError("password length must be between 8 and 50")
        return value


class RegisterByPasswordRequest(_IdentityRequest):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 50:
            raise ValueError("password length must be between 8 and 50")
        return value


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginTicketRequest(BaseModel):
    login_ticket: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 50:
            raise ValueError("new password length must be between 8 and 50")
        return value


class ChangePhoneRequest(BaseModel):
    phone: str
    code: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return _validate_phone(value) or value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _validate_code(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class UserInfoResponse(BaseModel):
    id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    roles: List[str] = []
    store_id: Optional[str] = None
    created_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    message: str


class QrGenerateResponse(BaseModel):
    qr_id: str
    qr_url: str
    qr_image: str
    expires_in: int


class QrStatusResponse(BaseModel):
    status: str
    tokens: Optional[dict] = None
    login_ticket: Optional[str] = None
    user_name: Optional[str] = None


class QrConfirmRequest(BaseModel):
    qr_id: str


class WechatQrResponse(BaseModel):
    qr_url: str
    state: str
    expires_in: int


class WechatStatusResponse(BaseModel):
    status: str
    tokens: Optional[dict] = None
    login_ticket: Optional[str] = None
    message: Optional[str] = None


class WechatBindPasswordRequest(_IdentityRequest):
    state: str
    password: str
