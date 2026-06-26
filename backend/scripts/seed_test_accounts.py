"""Seed production smoke-test accounts.

Run inside the backend container:
    python scripts/seed_test_accounts.py

Optional environment overrides:
    KELIU_MERCHANT_PHONE
    KELIU_MERCHANT_PASSWORD  required
    KELIU_ADMIN_PHONE
    KELIU_ADMIN_PASSWORD     required
"""
from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta

from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.db.session import get_session_factory
from app.models.store import Store
from app.models.subscription import Subscription
from app.models.user import Role, User, UserRole


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


MERCHANT_PHONE = os.getenv("KELIU_MERCHANT_PHONE", "13800000001")
MERCHANT_PASSWORD = required_env("KELIU_MERCHANT_PASSWORD")
ADMIN_PHONE = os.getenv("KELIU_ADMIN_PHONE", "18626834206")
ADMIN_PASSWORD = required_env("KELIU_ADMIN_PASSWORD")


async def get_or_create_role(db, name: str, description: str) -> Role:
    role = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
    if role is None:
        role = Role(name=name, description=description)
        db.add(role)
        await db.flush()
    return role


def needs_password_update(user: User, plain_password: str) -> bool:
    if not user.password_hash:
        return True
    try:
        return not verify_password(plain_password, user.password_hash)
    except Exception:
        return True


async def upsert_user(db, phone: str, password: str, name: str) -> User:
    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if user is None:
        user = User(
            phone=phone,
            name=name,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(user)
        await db.flush()
        return user

    user.name = name
    user.is_active = True
    if needs_password_update(user, password):
        user.password_hash = hash_password(password)
    return user


async def ensure_user_role(db, user: User, role: Role, store_id: str | None) -> None:
    user_role = (
        await db.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )
    ).scalar_one_or_none()

    if user_role is None:
        db.add(UserRole(user_id=user.id, role_id=role.id, store_id=store_id))
    else:
        user_role.store_id = store_id


async def ensure_store(db, owner: User) -> Store:
    store = (
        await db.execute(select(Store).where(Store.owner_id == owner.id))
    ).scalars().first()
    if store is None:
        store = Store(
            name="Test Store",
            address="Online Test Address",
            industry_type="restaurant",
            owner_id=owner.id,
        )
        db.add(store)
        await db.flush()
    else:
        store.owner_id = owner.id
        store.name = store.name or "Test Store"
    return store


async def ensure_subscription(db, store: Store) -> None:
    subscription = (
        await db.execute(select(Subscription).where(Subscription.store_id == store.id))
    ).scalar_one_or_none()
    if subscription is None:
        db.add(
            Subscription(
                store_id=store.id,
                plan_name="basic",
                customer_limit=10000,
                status="active",
                quota_date=date.today(),
                next_billing_date=date.today() + timedelta(days=30),
                restrictions="",
            )
        )
        return

    subscription.plan_name = "basic"
    subscription.customer_limit = 10000
    subscription.status = "active"
    subscription.restrictions = ""
    subscription.next_billing_date = date.today() + timedelta(days=30)


async def main() -> None:
    session_factory = get_session_factory()
    async with session_factory() as db:
        roles = {
            "super_admin": await get_or_create_role(db, "super_admin", "Super admin"),
            "store_owner": await get_or_create_role(db, "store_owner", "Store owner"),
            "staff": await get_or_create_role(db, "staff", "Staff"),
            "partner": await get_or_create_role(db, "partner", "Partner"),
            "association": await get_or_create_role(db, "association", "Association"),
        }

        admin = await upsert_user(db, ADMIN_PHONE, ADMIN_PASSWORD, "System Admin")
        await ensure_user_role(db, admin, roles["super_admin"], None)

        merchant = await upsert_user(db, MERCHANT_PHONE, MERCHANT_PASSWORD, "Test Merchant")
        store = await ensure_store(db, merchant)
        await ensure_user_role(db, merchant, roles["store_owner"], store.id)
        await ensure_subscription(db, store)

        await db.commit()

        print("Seeded smoke-test accounts.")
        print(f"merchant={MERCHANT_PHONE}")
        print(f"admin={ADMIN_PHONE}")
        print(f"store_id={store.id}")


if __name__ == "__main__":
    asyncio.run(main())
