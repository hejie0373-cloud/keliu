import unittest
import sys
from datetime import datetime
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

fastapi_stub = ModuleType("fastapi")


class _HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


fastapi_stub.HTTPException = _HTTPException
fastapi_stub.status = SimpleNamespace(
    HTTP_400_BAD_REQUEST=400,
    HTTP_401_UNAUTHORIZED=401,
    HTTP_403_FORBIDDEN=403,
    HTTP_404_NOT_FOUND=404,
    HTTP_429_TOO_MANY_REQUESTS=429,
    HTTP_500_INTERNAL_SERVER_ERROR=500,
)
sys.modules["fastapi"] = fastapi_stub


class _Statement:
    def where(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self


sqlalchemy_stub = ModuleType("sqlalchemy")
sqlalchemy_stub.select = lambda *_args, **_kwargs: _Statement()
sys.modules["sqlalchemy"] = sqlalchemy_stub

sqlalchemy_ext_stub = ModuleType("sqlalchemy.ext")
sqlalchemy_asyncio_stub = ModuleType("sqlalchemy.ext.asyncio")
sqlalchemy_asyncio_stub.AsyncSession = object
sys.modules["sqlalchemy.ext"] = sqlalchemy_ext_stub
sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy_asyncio_stub

security_stub = ModuleType("app.core.security")
security_stub.create_access_token = lambda data: ("access", "access_jti", 1800)
security_stub.create_refresh_token = lambda user_id: ("refresh", "refresh_jti")
security_stub.decode_token = lambda token: {}
security_stub.get_refresh_token_ttl = lambda payload: 0
security_stub.hash_password = lambda value: f"hashed:{value}"
security_stub.verify_password = lambda plain, hashed: False
sys.modules["app.core.security"] = security_stub

config_stub = ModuleType("app.core.config")
config_stub.settings = SimpleNamespace(ENVIRONMENT="development")
sys.modules["app.core.config"] = config_stub

models_stub = ModuleType("app.models.user")


class _Column:
    def __eq__(self, _other):
        return True

    def isnot(self, _other):
        return True


class _User:
    id = _Column()
    phone = _Column()
    email = _Column()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if "id" not in kwargs:
            self.id = "new_user"


class _UserIdentity:
    type = _Column()
    identifier = _Column()
    user_id = _Column()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.verified_at = kwargs.get("verified_at", datetime.utcnow())


class _Role:
    name = _Column()
    id = _Column()


class _UserRole:
    user_id = _Column()
    store_id = _Column()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


models_stub.Role = _Role
models_stub.User = _User
models_stub.UserIdentity = _UserIdentity
models_stub.UserRole = _UserRole
sys.modules["app.models.user"] = models_stub

schemas_stub = ModuleType("app.schemas.auth")


class TokenResponse:
    def __init__(self, access_token, refresh_token=None, expires_in=1800, token_type="bearer"):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.token_type = token_type

    def model_dump(self):
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "token_type": self.token_type,
        }


schemas_stub.TokenResponse = TokenResponse
schemas_stub.UserInfoResponse = lambda **kwargs: SimpleNamespace(**kwargs)
sys.modules["app.schemas.auth"] = schemas_stub

redis_stub = ModuleType("app.utils.redis_client")
redis_stub.add_to_blacklist = AsyncMock()
redis_stub.add_family_to_blacklist = AsyncMock()
redis_stub.check_otp_rate_limit = AsyncMock(return_value=True)
redis_stub.check_sms_rate_limit = AsyncMock(return_value=True)
redis_stub.delete_otp_code = AsyncMock()
redis_stub.delete_sms_code = AsyncMock()
redis_stub.is_blacklisted = AsyncMock(return_value=False)
redis_stub.is_family_blacklisted = AsyncMock(return_value=False)
redis_stub.store_otp_code = AsyncMock()
redis_stub.store_sms_code = AsyncMock()
redis_stub.verify_otp_code = AsyncMock(return_value=False)
redis_stub.verify_sms_code = AsyncMock(return_value=False)
sys.modules["app.utils.redis_client"] = redis_stub

notification_stub = ModuleType("app.services.notification_service")


class _EmailProvider:
    async def send(self, _to, _content):
        return True


class _SMSProvider:
    async def send(self, _to, _content):
        return True


notification_stub.EmailProvider = _EmailProvider
notification_stub.SMSProvider = _SMSProvider
sys.modules["app.services.notification_service"] = notification_stub

from app.services import auth_service


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _QueuedSession:
    def __init__(self, *results):
        self._results = list(results)
        self.added = []
        self.flushed = False
        self.committed = False
        self.refreshed = []

    async def execute(self, _statement):
        if not self._results:
            raise AssertionError("No queued DB result")
        return _ScalarResult(self._results.pop(0))

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    async def refresh(self, value):
        self.refreshed.append(value)


class AuthIdentityTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_identity_supports_phone_and_email(self):
        self.assertEqual(
            auth_service.normalize_identity(" 13800138000 "),
            ("phone", "13800138000"),
        )
        self.assertEqual(
            auth_service.normalize_identity(" User.Name@Example.COM "),
            ("email", "user.name@example.com"),
        )

    async def test_send_email_code_uses_purpose_scoped_otp_key(self):
        with patch.object(auth_service, "generate_verification_code", return_value="123456"), \
             patch.object(auth_service, "check_otp_rate_limit", new=AsyncMock(return_value=True), create=True) as rate_limit, \
             patch.object(auth_service, "store_otp_code", new=AsyncMock(), create=True) as store_code, \
             patch("app.services.notification_service.EmailProvider") as provider_cls:
            provider_cls.return_value.send = AsyncMock(return_value=True)

            code = await auth_service.send_verification_code("User.Name@Example.COM", purpose="register")

        self.assertEqual(code, "123456")
        rate_limit.assert_awaited_once_with("register", "email", "user.name@example.com")
        store_code.assert_awaited_once_with("register", "email", "user.name@example.com", "123456")
        provider_cls.return_value.send.assert_awaited_once_with("user.name@example.com", "123456")

    async def test_login_by_password_accepts_verified_email_identity(self):
        user = SimpleNamespace(id="user_1", is_active=True, password_hash="hashed")
        identity = SimpleNamespace(user_id="user_1", verified_at="2026-07-03T00:00:00")
        db = _QueuedSession(identity, user)
        token = TokenResponse(access_token="access", refresh_token="refresh", expires_in=1800)

        with patch.object(auth_service, "verify_password", return_value=True), \
             patch.object(auth_service, "_generate_token_response", new=AsyncMock(return_value=token)):
            result = await auth_service.login_by_password(
                account="User.Name@Example.COM",
                password="correct-password",
                db=db,
            )

        self.assertEqual(result.access_token, "access")

    async def test_register_by_password_creates_local_email_user(self):
        role = SimpleNamespace(id="role_1")
        db = _QueuedSession(None, None, None, role)
        token = TokenResponse(access_token="access", refresh_token="refresh", expires_in=1800)

        with patch.object(auth_service, "_generate_token_response", new=AsyncMock(return_value=token)):
            result = await auth_service.register_by_password(
                account="User.Name@Example.COM",
                password="correct-password",
                db=db,
            )

        self.assertEqual(result.access_token, "access")
        self.assertTrue(db.flushed)
        self.assertTrue(db.committed)
        self.assertEqual(db.added[0].email, "user.name@example.com")
        self.assertEqual(db.added[0].password_hash, "hashed:correct-password")
        self.assertEqual(db.added[1].type, "email")
        self.assertEqual(db.added[1].identifier, "user.name@example.com")
        self.assertEqual(db.added[2].role_id, "role_1")

    async def test_refresh_reuse_revokes_session_family(self):
        user = SimpleNamespace(id="user_1", is_active=True)
        db = _QueuedSession(user)
        payload = {
            "type": "refresh",
            "jti": "old_jti",
            "sub": "user_1",
            "family": "family_1",
            "exp": 1893456000,
        }

        with patch.object(auth_service, "decode_token", return_value=payload), \
             patch.object(auth_service, "is_family_blacklisted", new=AsyncMock(return_value=False)), \
             patch.object(auth_service, "is_blacklisted", new=AsyncMock(return_value=True)), \
             patch.object(auth_service, "add_family_to_blacklist", new=AsyncMock()) as family_blacklist:
            with self.assertRaises(_HTTPException) as raised:
                await auth_service.refresh_access_token("reused-refresh", db)

        self.assertEqual(raised.exception.detail, "TOKEN_REUSE_DETECTED")
        family_blacklist.assert_awaited_once()

    def test_token_response_can_hide_refresh_token_for_cookie_sessions(self):
        token = TokenResponse(access_token="access", refresh_token="refresh", expires_in=1800)

        public_token = auth_service.public_token_response(token)

        self.assertEqual(public_token.access_token, "access")
        self.assertIsNone(public_token.refresh_token)

    def test_refresh_cookie_options_are_http_only(self):
        options = auth_service.refresh_cookie_options(max_age=604800)

        self.assertEqual(options["key"], "refresh_token")
        self.assertTrue(options["httponly"])
        self.assertEqual(options["samesite"], "lax")
        self.assertEqual(options["max_age"], 604800)


if __name__ == "__main__":
    unittest.main()
