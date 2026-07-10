"""WeChat OAuth QR login service."""
import json
import logging
import secrets
from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.user import Role, User, UserIdentity, UserRole
from app.services.auth_service import normalize_identity
from app.services.qr_auth_service import create_login_ticket
from app.utils.redis_client import get_redis

logger = logging.getLogger(__name__)

WECHAT_STATE_PREFIX = "wechat_state:"
WECHAT_STATE_TTL = 300


def _state_key(state: str) -> str:
    return f"{WECHAT_STATE_PREFIX}{state}"


async def generate_qr_url() -> dict:
    """Generate a WeChat OAuth URL and initialize its polling state."""
    if not settings.WECHAT_APP_ID or not settings.WECHAT_APP_SECRET or not settings.WECHAT_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WECHAT_CONFIG_MISSING",
        )

    state = secrets.token_urlsafe(16)
    query = urlencode({
        "appid": settings.WECHAT_APP_ID,
        "redirect_uri": settings.WECHAT_REDIRECT_URI,
        "response_type": "code",
        "scope": "snsapi_userinfo",
        "state": state,
    })
    qr_url = f"https://open.weixin.qq.com/connect/oauth2/authorize?{query}#wechat_redirect"

    r = await get_redis()
    await r.setex(_state_key(state), WECHAT_STATE_TTL, json.dumps({"status": "pending"}, ensure_ascii=False))
    return {"qr_url": qr_url, "state": state, "expires_in": WECHAT_STATE_TTL}


async def handle_callback(code: str, state: str, db: AsyncSession) -> bool:
    """Handle WeChat OAuth callback and write the login result into Redis."""
    r = await get_redis()
    data_raw = await r.get(_state_key(state))
    if not data_raw:
        logger.warning("WeChat login state expired or invalid: %s", state)
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_res = await client.get(
                "https://api.weixin.qq.com/sns/oauth2/access_token",
                params={
                    "appid": settings.WECHAT_APP_ID,
                    "secret": settings.WECHAT_APP_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_res.json()
            if "errcode" in token_data:
                logger.warning("WeChat access_token exchange failed: %s", token_data)
                return False

            access_token = token_data["access_token"]
            openid = token_data["openid"]
            user_res = await client.get(
                "https://api.weixin.qq.com/sns/userinfo",
                params={"access_token": access_token, "openid": openid, "lang": "zh_CN"},
            )
            user_data = user_res.json()
            if "errcode" in user_data:
                logger.warning("WeChat userinfo fetch failed: %s", user_data)
                return False
    except Exception as exc:
        logger.exception("WeChat callback failed: %s", exc)
        return False

    user = await _find_existing_wechat_user(openid, user_data, db)
    if not user:
        await r.setex(
            _state_key(state),
            120,
            json.dumps(
                {
                    "status": "unbound",
                    "openid": openid,
                    "user_data": user_data,
                    "message": "WECHAT_ACCOUNT_NOT_BOUND",
                },
                ensure_ascii=False,
            ),
        )
        return True

    tokens = await _create_tokens_for_user(user, db)
    login_ticket = await create_login_ticket(tokens)
    await r.setex(
        _state_key(state),
        30,
        json.dumps({"status": "confirmed", "login_ticket": login_ticket}, ensure_ascii=False),
    )
    return True


async def get_login_status(state: str) -> dict:
    """Read WeChat QR login polling status."""
    r = await get_redis()
    data_raw = await r.get(_state_key(state))
    if not data_raw:
        return {"status": "expired"}
    return json.loads(data_raw)


async def bind_wechat_by_password(state: str, account: str, password: str, db: AsyncSession) -> dict:
    """Bind a scanned WeChat identity to an existing account."""
    r = await get_redis()
    data_raw = await r.get(_state_key(state))
    if not data_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WECHAT_STATE_EXPIRED")

    state_data = json.loads(data_raw)
    if state_data.get("status") != "unbound" or not state_data.get("openid"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WECHAT_STATE_NOT_BINDABLE")

    identity_type, identifier = normalize_identity(account)
    identity_result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.type == identity_type,
            UserIdentity.identifier == identifier,
        )
    )
    identity = identity_result.scalar_one_or_none()
    user = identity.user if identity and identity.verified_at else None
    if not user:
        fallback_column = User.phone if identity_type == "phone" else User.email
        result = await db.execute(select(User).where(fallback_column == identifier))
        user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="USER_DISABLED")

    await _bind_wechat_to_user(user, state_data["openid"], state_data.get("user_data") or {}, db)

    tokens = await _create_tokens_for_user(user, db)
    login_ticket = await create_login_ticket(tokens)
    await r.setex(
        _state_key(state),
        30,
        json.dumps({"status": "confirmed", "login_ticket": login_ticket}, ensure_ascii=False),
    )
    return {"status": "confirmed", "login_ticket": login_ticket}


async def _find_existing_wechat_user(openid: str, user_data: dict, db: AsyncSession) -> User | None:
    """Find an existing account for WeChat login; never create a merchant account here."""
    identity_result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.type == "wechat",
            UserIdentity.identifier == openid,
        )
    )
    identity = identity_result.scalar_one_or_none()
    if identity and identity.verified_at:
        user = identity.user
        if not user.is_active:
            logger.warning("WeChat identity matched a disabled account: user_id=%s", user.id)
            return None
        await _bind_wechat_to_user(user, openid, user_data, db)
        return user

    result = await db.execute(select(User).where(User.wechat_openid == openid))
    user = result.scalar_one_or_none()
    if user:
        if not user.is_active:
            logger.warning("WeChat openid matched a disabled account: user_id=%s", user.id)
            return None
        await _bind_wechat_to_user(user, openid, user_data, db)
        logger.info("WeChat login matched existing openid account: openid=%s user_id=%s", openid, user.id)
        return user

    logger.info("WeChat login openid is not bound to an existing account: openid=%s", openid)
    return None


def _extract_phone(user_data: dict) -> str:
    for key in ("phone", "phone_number", "phoneNumber", "mobile", "pure_phone_number", "purePhoneNumber"):
        value = str(user_data.get(key) or "").strip()
        if value.startswith("+86"):
            value = value[3:]
        if value.isdigit() and len(value) == 11:
            return value
    return ""


async def _bind_wechat_to_user(user: User, openid: str, user_data: dict, db: AsyncSession) -> None:
    existing = await db.execute(select(User).where(User.wechat_openid == openid))
    existing_user = existing.scalar_one_or_none()
    if existing_user and existing_user.id != user.id:
        existing_user.wechat_openid = None
        await db.flush()

    identity_result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.type == "wechat",
            UserIdentity.identifier == openid,
        )
    )
    identity = identity_result.scalar_one_or_none()
    if identity and identity.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="WECHAT_ALREADY_BOUND")
    if not identity:
        db.add(UserIdentity(
            user_id=user.id,
            type="wechat",
            identifier=openid,
            verified_at=datetime.utcnow(),
            is_primary=False,
        ))
    else:
        identity.verified_at = identity.verified_at or datetime.utcnow()

    nickname = user_data.get("nickname") or user.wechat_nickname or "微信用户"
    avatar = user_data.get("headimgurl") or user.wechat_avatar
    user.wechat_openid = openid
    user.wechat_nickname = nickname
    user.wechat_avatar = avatar
    if avatar and not user.avatar_url:
        user.avatar_url = avatar
    await db.commit()
    await db.refresh(user)


async def _create_tokens_for_user(user: User, db: AsyncSession) -> dict:
    roles_result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    role_names = [row[0] for row in roles_result.all()]

    store_result = await db.execute(
        select(UserRole.store_id).where(
            UserRole.user_id == user.id,
            UserRole.store_id.isnot(None),
        ).limit(1)
    )
    store_id = store_result.scalar_one_or_none()

    payload = {"sub": user.id, "roles": role_names}
    if store_id:
        payload["store_id"] = store_id

    access_token, _, expires_in = create_access_token(payload)
    refresh_token, _ = create_refresh_token(user.id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }
