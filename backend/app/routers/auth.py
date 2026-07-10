"""Authentication routes."""
from typing import Optional

from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginByPasswordRequest,
    LoginByPhoneRequest,
    LoginTicketRequest,
    LogoutRequest,
    MessageResponse,
    QrConfirmRequest,
    QrGenerateResponse,
    QrStatusResponse,
    RefreshTokenRequest,
    RegisterByPasswordRequest,
    RegisterByPhoneRequest,
    SendCodeRequest,
    TokenResponse,
    WechatBindPasswordRequest,
    WechatQrResponse,
    WechatStatusResponse,
)
from app.services.auth_service import (
    login_by_password,
    login_by_phone,
    logout,
    public_token_response,
    refresh_access_token,
    refresh_cookie_options,
    register_by_password,
    register_by_phone,
    send_verification_code,
)
from app.services.qr_auth_service import (
    confirm_qr_login,
    consume_login_ticket,
    generate_qr_session,
    get_qr_status,
)
from app.services.wechat_service import bind_wechat_by_password, generate_qr_url, get_login_status, handle_callback

router = APIRouter()


def _set_refresh_cookie(response: Response, refresh_token: Optional[str]) -> None:
    if refresh_token:
        response.set_cookie(value=refresh_token, **refresh_cookie_options())


@router.post("/send-code", response_model=MessageResponse, summary="Send OTP code")
@limiter.limit("3/minute")
async def send_code(request: Request, data: SendCodeRequest):
    code = await send_verification_code(data.identity_account, purpose=data.purpose)
    if settings.ENVIRONMENT == "development" and code:
        return MessageResponse(message=f"code sent: {code}")
    return MessageResponse(message="code sent")


@router.post("/login/phone", response_model=TokenResponse, summary="OTP login")
async def login_phone(
    response: Response,
    data: LoginByPhoneRequest,
    db: AsyncSession = Depends(get_db),
):
    token_response = await login_by_phone(phone=data.identity_account, code=data.code, db=db)
    _set_refresh_cookie(response, token_response.get("refresh_token"))
    token_response["refresh_token"] = None
    return token_response


@router.post("/login/password", response_model=TokenResponse, summary="Password login")
@limiter.limit("5/minute")
async def login_password(
    request: Request,
    response: Response,
    data: LoginByPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    token_response = await login_by_password(account=data.identity_account, password=data.password, db=db)
    _set_refresh_cookie(response, token_response.refresh_token)
    return public_token_response(token_response)


@router.post("/register/phone", response_model=TokenResponse, status_code=201, summary="Account registration")
async def register_phone(
    response: Response,
    data: RegisterByPhoneRequest,
    db: AsyncSession = Depends(get_db),
):
    token_response = await register_by_phone(account=data.identity_account, code=data.code, password=data.password, db=db)
    _set_refresh_cookie(response, token_response.refresh_token)
    return public_token_response(token_response)


@router.post("/register/password", response_model=TokenResponse, status_code=201, summary="Password registration")
async def register_password(
    response: Response,
    data: RegisterByPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    token_response = await register_by_password(account=data.identity_account, password=data.password, db=db)
    _set_refresh_cookie(response, token_response.refresh_token)
    return public_token_response(token_response)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh(
    response: Response,
    data: Optional[RefreshTokenRequest] = Body(default=None),
    refresh_cookie: Optional[str] = Cookie(default=None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
):
    refresh_token = data.refresh_token if data else refresh_cookie
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="REFRESH_TOKEN_REQUIRED")
    token_response = await refresh_access_token(refresh_token=refresh_token, db=db)
    _set_refresh_cookie(response, token_response.refresh_token)
    return public_token_response(token_response)


@router.post("/login-ticket/exchange", response_model=TokenResponse, summary="Exchange login ticket")
async def exchange_login_ticket(
    response: Response,
    data: LoginTicketRequest,
):
    tokens = await consume_login_ticket(data.login_ticket)
    if not tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LOGIN_TICKET_INVALID")
    token_response = TokenResponse(**tokens)
    _set_refresh_cookie(response, token_response.refresh_token)
    return public_token_response(token_response)


@router.post("/logout", response_model=MessageResponse, summary="Logout")
async def logout_endpoint(
    response: Response,
    data: Optional[LogoutRequest] = Body(default=None),
    refresh_cookie: Optional[str] = Cookie(default=None, alias="refresh_token"),
):
    refresh_token = data.refresh_token if data else refresh_cookie
    if refresh_token:
        await logout(refresh_token=refresh_token)
    response.delete_cookie(key="refresh_token", path="/api/auth", samesite="lax")
    return MessageResponse(message="logout success")


@router.post("/qr/generate", response_model=QrGenerateResponse, summary="Generate QR login")
async def generate_qr(request: Request):
    return await generate_qr_session()


@router.get("/qr/status/{qr_id}", response_model=QrStatusResponse, summary="Get QR login status")
async def get_qr_status_endpoint(qr_id: str):
    return await get_qr_status(qr_id)


@router.post("/qr/confirm", response_model=MessageResponse, summary="Confirm QR login")
async def confirm_qr(
    data: QrConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result_store = await db.execute(
        select(UserRole).where(
            UserRole.user_id == current_user.id,
            UserRole.store_id.isnot(None),
        ).limit(1)
    )
    user_role = result_store.scalar_one_or_none()
    store_id = user_role.store_id if user_role else None

    result = await confirm_qr_login(
        qr_id=data.qr_id,
        user_id=str(current_user.id),
        user_name=current_user.name or current_user.phone or current_user.email or "user",
        store_id=store_id,
        db=db,
    )
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return MessageResponse(message="qr login confirmed")


@router.get("/wechat/qr-url", response_model=WechatQrResponse, summary="Get WeChat QR URL")
async def get_wechat_qr_url():
    return await generate_qr_url()


@router.get("/wechat/callback", summary="WeChat OAuth callback")
async def wechat_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    signature: Optional[str] = None,
    timestamp: Optional[str] = None,
    nonce: Optional[str] = None,
    echostr: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    if echostr and signature and timestamp and nonce:
        from .wechat_verify import verify_wechat_signature
        if verify_wechat_signature(signature, timestamp, nonce):
            return HTMLResponse(content=echostr, media_type="text/plain; charset=utf-8")
        return HTMLResponse(content="fail", media_type="text/plain; charset=utf-8")

    if not code or not state:
        return HTMLResponse(content="<html><body><h2>Please scan with WeChat</h2></body></html>", media_type="text/html; charset=utf-8")

    success = await handle_callback(code=code, state=state, db=db)
    if success:
        return HTMLResponse(
            content="<html><body><h2>Login confirmed. Return to your browser.</h2></body></html>",
            media_type="text/html; charset=utf-8",
        )
    return HTMLResponse(
        content="<html><body><h2>Login failed. Please retry.</h2></body></html>",
        status_code=400,
        media_type="text/html; charset=utf-8",
    )


@router.get("/wechat/status/{state}", response_model=WechatStatusResponse, summary="Get WeChat login status")
async def get_wechat_status(state: str):
    return await get_login_status(state)


@router.post("/wechat/bind-password", response_model=WechatStatusResponse, summary="Bind WeChat to account")
async def bind_wechat_password(
    data: WechatBindPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    return await bind_wechat_by_password(
        state=data.state,
        account=data.identity_account,
        password=data.password,
        db=db,
    )
