"""Authentication service: OTP, password login, registration, refresh, logout."""
import logging
import random
import re
import secrets
import string
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_refresh_token_ttl,
    hash_password,
    verify_password,
)
from app.models.user import Role, User, UserIdentity, UserRole
from app.schemas.auth import TokenResponse, UserInfoResponse
from app.utils.redis_client import (
    add_to_blacklist,
    add_family_to_blacklist,
    check_otp_rate_limit,
    delete_otp_code,
    is_blacklisted,
    is_family_blacklisted,
    store_otp_code,
    verify_otp_code,
)

logger = logging.getLogger(__name__)

OTP_PURPOSES = {"login", "register", "reset_password", "bind_identity", "change_phone"}


def generate_verification_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def normalize_identity(account: str) -> tuple[str, str]:
    """Normalize a login identifier into (type, identifier)."""
    value = (account or "").strip()
    if re.match(r"^1[3-9]\d{9}$", value):
        return "phone", value

    email = value.lower()
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return "email", email

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ACCOUNT_FORMAT_INVALID")


async def send_verification_code(account: str, purpose: str = "login") -> str:
    """Send a purpose-scoped OTP to a phone number or email address."""
    if purpose not in OTP_PURPOSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP_PURPOSE_INVALID")

    identity_type, identifier = normalize_identity(account)
    if not await check_otp_rate_limit(purpose, identity_type, identifier):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="OTP_RATE_LIMITED")

    code = generate_verification_code()
    await store_otp_code(purpose, identity_type, identifier, code)

    if settings.ENVIRONMENT == "development":
        logger.info("[DEV] verification_code purpose=%s %s=%s code=%s", purpose, identity_type, identifier, code)

    from app.services.notification_service import EmailProvider, SMSProvider

    provider = SMSProvider() if identity_type == "phone" else EmailProvider()
    success = await provider.send(identifier, code)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OTP_SEND_FAILED")

    return code if settings.ENVIRONMENT == "development" else ""


async def login_by_phone(phone: str, code: str, db: AsyncSession) -> dict:
    token_response = await login_by_otp(account=phone, code=code, db=db)
    return {"is_new_user": False, **token_response.model_dump()}


async def login_by_otp(account: str, code: str, db: AsyncSession) -> TokenResponse:
    identity_type, identifier = normalize_identity(account)
    if not await verify_otp_code("login", identity_type, identifier, code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP_INVALID_OR_EXPIRED")

    user = await _get_verified_user_by_identity(identity_type, identifier, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ACCOUNT_NOT_REGISTERED")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="USER_DISABLED")

    await delete_otp_code("login", identity_type, identifier)
    return await _generate_token_response(user, db)


async def login_by_password(
    phone: str | None = None,
    password: str = "",
    db: AsyncSession | None = None,
    account: str | None = None,
) -> TokenResponse:
    identity_type, identifier = normalize_identity(account or phone or "")
    user = await _get_verified_user_by_identity(identity_type, identifier, db)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ACCOUNT_OR_PASSWORD_INVALID")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="USER_DISABLED")

    return await _generate_token_response(user, db)


async def register_by_phone(
    phone: str | None = None,
    code: str = "",
    password: str = "",
    db: AsyncSession | None = None,
    account: str | None = None,
) -> TokenResponse:
    account_value = account or phone or ""
    identity_type, identifier = normalize_identity(account_value)
    if not await verify_otp_code("register", identity_type, identifier, code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP_INVALID_OR_EXPIRED")

    if await _get_verified_user_by_identity(identity_type, identifier, db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ACCOUNT_ALREADY_REGISTERED")

    user_kwargs = {
        "name": _default_user_name(identity_type, identifier),
        "password_hash": hash_password(password),
        "is_active": True,
    }
    if identity_type == "phone":
        user_kwargs["phone"] = identifier
    else:
        user_kwargs["email"] = identifier

    user = User(**user_kwargs)
    db.add(user)
    await db.flush()
    await _add_identity(user, identity_type, identifier, db, is_primary=True)

    result = await db.execute(select(Role).where(Role.name == "store_owner"))
    store_owner_role = result.scalar_one_or_none()
    if store_owner_role:
        db.add(UserRole(user_id=user.id, role_id=store_owner_role.id, store_id=None))

    await db.commit()
    await db.refresh(user)
    await delete_otp_code("register", identity_type, identifier)
    return await _generate_token_response(user, db)


async def register_by_password(account: str, password: str, db: AsyncSession) -> TokenResponse:
    identity_type, identifier = normalize_identity(account)
    if await _get_verified_user_by_identity(identity_type, identifier, db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ACCOUNT_ALREADY_REGISTERED")

    user_kwargs = {
        "name": _default_user_name(identity_type, identifier),
        "password_hash": hash_password(password),
        "is_active": True,
    }
    if identity_type == "phone":
        user_kwargs["phone"] = identifier
    else:
        user_kwargs["email"] = identifier

    user = User(**user_kwargs)
    db.add(user)
    await db.flush()
    await _add_identity(user, identity_type, identifier, db, is_primary=True)

    result = await db.execute(select(Role).where(Role.name == "store_owner"))
    store_owner_role = result.scalar_one_or_none()
    if store_owner_role:
        db.add(UserRole(user_id=user.id, role_id=store_owner_role.id, store_id=None))

    await db.commit()
    await db.refresh(user)
    return await _generate_token_response(user, db)


async def refresh_access_token(refresh_token: str, db: AsyncSession) -> TokenResponse:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOKEN_TYPE_INVALID")

    jti = payload.get("jti")
    user_id = payload.get("sub")
    family_id = payload.get("family") or jti
    if not jti or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOKEN_INVALID")

    if family_id and await is_family_blacklisted(family_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOKEN_REVOKED")

    if await is_blacklisted(jti):
        if family_id:
            await add_family_to_blacklist(family_id, get_refresh_token_ttl(payload))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOKEN_REUSE_DETECTED")

    await add_to_blacklist(jti, get_refresh_token_ttl(payload))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="USER_NOT_FOUND_OR_DISABLED")

    return await _generate_token_response(user, db, refresh_family_id=family_id)


async def logout(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
        jti = payload.get("jti")
        if jti:
            ttl = get_refresh_token_ttl(payload)
            await add_to_blacklist(jti, ttl)
            logger.info("refresh token blacklisted: jti=%s ttl=%ss", jti, ttl)
    except Exception:
        pass
    return {"message": "logout success"}


def public_token_response(token_response: TokenResponse) -> TokenResponse:
    """Return only the browser-readable access token payload."""
    return TokenResponse(
        access_token=token_response.access_token,
        refresh_token=None,
        token_type=token_response.token_type,
        expires_in=token_response.expires_in,
    )


def refresh_cookie_options(max_age: int | None = None) -> dict:
    return {
        "key": "refresh_token",
        "httponly": True,
        "secure": settings.ENVIRONMENT != "development",
        "samesite": "lax",
        "max_age": max_age if max_age is not None else settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        "path": "/api/auth",
    }


async def get_user_info(user: User, db: AsyncSession) -> UserInfoResponse:
    result = await db.execute(select(UserRole).where(UserRole.user_id == user.id))
    user_roles = result.scalars().all()

    roles = []
    store_id = None
    for user_role in user_roles:
        role_result = await db.execute(select(Role).where(Role.id == user_role.role_id))
        role = role_result.scalar_one_or_none()
        if role:
            roles.append(role.name)
        if store_id is None and user_role.store_id:
            store_id = user_role.store_id

    return UserInfoResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=getattr(user, "email", None),
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        roles=roles,
        store_id=store_id,
        created_at=user.created_at,
    )


async def _get_verified_user_by_identity(identity_type: str, identifier: str, db: AsyncSession) -> User | None:
    result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.type == identity_type,
            UserIdentity.identifier == identifier,
        )
    )
    identity = result.scalar_one_or_none()
    if identity and identity.verified_at:
        result = await db.execute(select(User).where(User.id == identity.user_id))
        return result.scalar_one_or_none()

    fallback_column = User.phone if identity_type == "phone" else User.email
    result = await db.execute(select(User).where(fallback_column == identifier))
    return result.scalar_one_or_none()


async def _add_identity(
    user: User,
    identity_type: str,
    identifier: str,
    db: AsyncSession,
    is_primary: bool = False,
) -> None:
    result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.type == identity_type,
            UserIdentity.identifier == identifier,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="IDENTITY_ALREADY_BOUND")
        existing.verified_at = existing.verified_at or datetime.utcnow()
        existing.is_primary = existing.is_primary or is_primary
        return

    db.add(UserIdentity(
        user_id=user.id,
        type=identity_type,
        identifier=identifier,
        verified_at=datetime.utcnow(),
        is_primary=is_primary,
    ))


def _default_user_name(identity_type: str, identifier: str) -> str:
    if identity_type == "phone":
        suffix = identifier[-4:]
    else:
        suffix = identifier.split("@", 1)[0][:12]
    return f"user_{suffix}_{secrets.token_hex(2)}"


async def _generate_token_response(user: User, db: AsyncSession, refresh_family_id: str | None = None) -> TokenResponse:
    result = await db.execute(select(UserRole).where(UserRole.user_id == user.id))
    user_roles = result.scalars().all()

    role_names = []
    store_id = None
    for user_role in user_roles:
        role_result = await db.execute(select(Role).where(Role.id == user_role.role_id))
        role = role_result.scalar_one_or_none()
        if role:
            role_names.append(role.name)
        if store_id is None and user_role.store_id:
            store_id = user_role.store_id

    token_data = {"sub": user.id, "roles": role_names}
    if store_id:
        token_data["store_id"] = store_id

    access_token, access_jti, expires_in = create_access_token(token_data)
    refresh_token, refresh_jti = create_refresh_token(user.id, family_id=refresh_family_id)
    logger.info("token generated user_id=%s access_jti=%s refresh_jti=%s", user.id, access_jti, refresh_jti)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )
