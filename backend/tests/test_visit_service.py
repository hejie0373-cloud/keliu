import unittest
from datetime import datetime
from types import ModuleType, SimpleNamespace
import sys
from unittest.mock import AsyncMock, patch

fastapi_stub = ModuleType("fastapi")


class _HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


fastapi_stub.HTTPException = _HTTPException
fastapi_stub.status = SimpleNamespace()
sys.modules["fastapi"] = fastapi_stub


class _Statement:
    def where(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self


sqlalchemy_stub = ModuleType("sqlalchemy")
sqlalchemy_stub.select = lambda *_args, **_kwargs: _Statement()
sqlalchemy_stub.desc = lambda value: value
sys.modules["sqlalchemy"] = sqlalchemy_stub

sqlalchemy_ext_stub = ModuleType("sqlalchemy.ext")
sqlalchemy_asyncio_stub = ModuleType("sqlalchemy.ext.asyncio")
sqlalchemy_asyncio_stub.AsyncSession = object
sys.modules["sqlalchemy.ext"] = sqlalchemy_ext_stub
sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy_asyncio_stub


class _Column:
    def __eq__(self, _other):
        return True


class _Customer:
    id = _Column()
    is_deleted = _Column()


class _Visit:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


models_stub = ModuleType("app.models.customer")
models_stub.Customer = _Customer
models_stub.Visit = _Visit
sys.modules["app.models.customer"] = models_stub

schema_stub = ModuleType("app.schemas.customer")
schema_stub.VisitCreate = object
schema_stub.VisitOut = object
sys.modules["app.schemas.customer"] = schema_stub

from app.services.visit_service import create_visit


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, customer):
        self.customer = customer
        self.added = None
        self.committed = False

    async def execute(self, _statement):
        return _ScalarResult(self.customer)

    def add(self, value):
        self.added = value

    async def commit(self):
        self.committed = True

    async def refresh(self, value):
        value.id = "visit_1"
        value.created_at = datetime(2026, 6, 30, 12, 0, 0)


class CreateVisitTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_visit_invalidates_customer_detail_cache(self):
        customer = SimpleNamespace(id="customer_1", store_id="store_1", is_deleted=False)
        db = _FakeSession(customer)
        data = SimpleNamespace(
            visited_at=datetime(2026, 6, 30, 10, 0, 0),
            service_type="剪发",
            staff_name=None,
            amount=88,
            payment_method=None,
            feedback=None,
        )

        with patch("app.utils.cache.delete", new=AsyncMock()) as cache_delete:
            await create_visit("customer_1", "store_1", data, db)

        cache_delete.assert_awaited_once_with("customer_detail:customer_1")


if __name__ == "__main__":
    unittest.main()
