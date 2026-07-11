import sys
import unittest
from datetime import datetime
from types import ModuleType, SimpleNamespace


fastapi_stub = ModuleType("fastapi")


class _HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


class _APIRouter:
    def get(self, *_args, **_kwargs):
        return lambda func: func

    def put(self, *_args, **_kwargs):
        return lambda func: func

    def post(self, *_args, **_kwargs):
        return lambda func: func


fastapi_stub.APIRouter = _APIRouter
fastapi_stub.Depends = lambda dependency=None: dependency
fastapi_stub.HTTPException = _HTTPException
sys.modules["fastapi"] = fastapi_stub


class _Column:
    def __eq__(self, _other):
        return True

    def is_(self, _other):
        return True

    def isnot(self, _other):
        return True


class _Statement:
    def where(self, *_args, **_kwargs):
        return self


sqlalchemy_stub = ModuleType("sqlalchemy")
sqlalchemy_stub.select = lambda *_args, **_kwargs: _Statement()
sys.modules["sqlalchemy"] = sqlalchemy_stub

sqlalchemy_ext_stub = ModuleType("sqlalchemy.ext")
sqlalchemy_asyncio_stub = ModuleType("sqlalchemy.ext.asyncio")
sqlalchemy_asyncio_stub.AsyncSession = object
sys.modules["sqlalchemy.ext"] = sqlalchemy_ext_stub
sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy_asyncio_stub

deps_stub = ModuleType("app.core.deps")
deps_stub.get_current_store_id = lambda: None
deps_stub.get_current_user = lambda: None
deps_stub.get_current_user_roles = lambda: []
sys.modules["app.core.deps"] = deps_stub

session_stub = ModuleType("app.db.session")
session_stub.get_db = lambda: None
sys.modules["app.db.session"] = session_stub


class _User:
    id = _Column()


class _Role:
    id = _Column()
    name = _Column()


class _UserRole:
    user_id = _Column()
    role_id = _Column()
    store_id = _Column()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


user_models_stub = ModuleType("app.models.user")
user_models_stub.User = _User
user_models_stub.UserRole = _UserRole
user_models_stub.Role = _Role
sys.modules["app.models.user"] = user_models_stub


class _Store:
    id = _Column()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = kwargs.get("id")
        self.logo_url = kwargs.get("logo_url")
        self.created_at = kwargs.get("created_at")


store_model_stub = ModuleType("app.models.store")
store_model_stub.Store = _Store
sys.modules["app.models.store"] = store_model_stub


class _Subscription:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


subscription_model_stub = ModuleType("app.models.subscription")
subscription_model_stub.Subscription = _Subscription
sys.modules["app.models.subscription"] = subscription_model_stub


class _StoreCreate:
    def __init__(self, name, address=None, industryType=None):
        self.name = name
        self.address = address
        self.industryType = industryType


class _StoreOut:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


store_schema_stub = ModuleType("app.schemas.store")
store_schema_stub.StoreCreate = _StoreCreate
store_schema_stub.StoreOut = _StoreOut
store_schema_stub.StoreUpdate = object
sys.modules["app.schemas.store"] = store_schema_stub

sys.modules.pop("app.routers.stores", None)
from app.routers.stores import create_store


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

    async def execute(self, _statement):
        if not self._results:
            raise AssertionError("No queued DB result")
        return _ScalarResult(self._results.pop(0))

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushed = True
        for value in self.added:
            if isinstance(value, _Store):
                value.id = "store_1"
                value.created_at = datetime(2026, 7, 6)

    async def commit(self):
        self.committed = True

    async def refresh(self, value):
        if isinstance(value, _Store):
            value.id = value.id or "store_1"
            value.created_at = value.created_at or datetime(2026, 7, 6)


class StoreCreateTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_store_binds_existing_unscoped_owner_role(self):
        existing_owner_role = _UserRole(user_id="user_1", role_id="role_1", store_id=None)
        db = _QueuedSession(
            None,
            SimpleNamespace(id="role_1"),
            existing_owner_role,
        )

        result = await create_store(
            data=_StoreCreate(name="刘老板的理发店", address="长沙", industryType="美容美发"),
            current_user=SimpleNamespace(id="user_1"),
            db=db,
        )

        added_user_roles = [value for value in db.added if isinstance(value, _UserRole)]
        self.assertEqual(result.id, "store_1")
        self.assertEqual(existing_owner_role.store_id, "store_1")
        self.assertEqual(added_user_roles, [])
        self.assertTrue(any(isinstance(value, _Subscription) for value in db.added))
        self.assertTrue(db.committed)


if __name__ == "__main__":
    unittest.main()
