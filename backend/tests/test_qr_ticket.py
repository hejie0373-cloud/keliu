import json
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, patch

qrcode_stub = ModuleType("qrcode")
qrcode_stub.make = lambda _value: SimpleNamespace(save=lambda *_args, **_kwargs: None)
sys.modules["qrcode"] = qrcode_stub

sqlalchemy_stub = ModuleType("sqlalchemy")


class _Statement:
    def join(self, *_args, **_kwargs):
        return self

    def where(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self


sqlalchemy_stub.select = lambda *_args, **_kwargs: _Statement()
sys.modules["sqlalchemy"] = sqlalchemy_stub

sqlalchemy_ext_stub = ModuleType("sqlalchemy.ext")
sqlalchemy_asyncio_stub = ModuleType("sqlalchemy.ext.asyncio")
sqlalchemy_asyncio_stub.AsyncSession = object
sys.modules["sqlalchemy.ext"] = sqlalchemy_ext_stub
sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy_asyncio_stub

config_stub = ModuleType("app.core.config")
config_stub.settings = SimpleNamespace(QR_CONFIRM_BASE_URL="http://localhost:5173")
sys.modules["app.core.config"] = config_stub

security_stub = ModuleType("app.core.security")
security_stub.create_access_token = lambda data: ("access", "access_jti", 1800)
security_stub.create_refresh_token = lambda user_id: ("refresh", "refresh_jti")
sys.modules["app.core.security"] = security_stub

models_stub = ModuleType("app.models.user")


class _Column:
    def __eq__(self, _other):
        return True

    def isnot(self, _other):
        return True


models_stub.Role = SimpleNamespace(name=_Column())
models_stub.UserRole = SimpleNamespace(role_id=_Column(), user_id=_Column(), store_id=_Column())
sys.modules["app.models.user"] = models_stub

redis_stub = ModuleType("app.utils.redis_client")
redis_stub.get_redis = AsyncMock()
sys.modules["app.utils.redis_client"] = redis_stub

from app.services import qr_auth_service


class _FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def setex(self, key, _ttl, value):
        self.values[key] = value


class QrTicketTests(unittest.IsolatedAsyncioTestCase):
    async def test_confirm_qr_login_stores_ticket_not_tokens(self):
        redis = _FakeRedis()
        qr_id = "qr_1"
        redis.values[qr_auth_service._qr_key(qr_id)] = json.dumps({"status": "pending"})

        with patch.object(qr_auth_service, "get_redis", new=AsyncMock(return_value=redis)):
            result = await qr_auth_service.confirm_qr_login(
                qr_id=qr_id,
                user_id="user_1",
                user_name="Demo",
                store_id=None,
                db=None,
            )

        stored = json.loads(redis.values[qr_auth_service._qr_key(qr_id)])
        self.assertTrue(result["success"])
        self.assertIn("login_ticket", stored)
        self.assertNotIn("tokens", stored)
        self.assertNotIn("tokens", result)


if __name__ == "__main__":
    unittest.main()
