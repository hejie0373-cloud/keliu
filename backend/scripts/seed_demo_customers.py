"""为测试店铺灌入演示客户数据（客户 + 到店记录 + AI 评分）。

在 backend 容器内运行：
    python scripts/seed_demo_customers.py

说明：
- 复用 seed_test_accounts.py 创建的测试商家店铺（默认手机号 13800000001）。
- 每个客户生成一段随时间分布的到店记录，并按「最近度/频率/趋势」算出
  一个近似的流失评分与 CLV，使前端「AI 记忆图谱」有真实可视内容。
- 幂等：重复运行会先清掉本店已有的演示客户（按手机号前缀识别），再重灌。

可选环境变量：
    KELIU_MERCHANT_PHONE   目标店铺的店主手机号（默认 13800000001）
    KELIU_DEMO_COUNT       生成客户数（默认 24）
"""
from __future__ import annotations

import asyncio
import os
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.ai_metric import AiMetric
from app.models.customer import Customer, Visit
from app.models.store import Store
from app.models.user import User

MERCHANT_PHONE = os.getenv("KELIU_MERCHANT_PHONE", "13800000001")
DEMO_COUNT = int(os.getenv("KELIU_DEMO_COUNT", "24"))

# 演示客户手机号前缀，用于幂等识别（避免误删真实数据）
DEMO_PHONE_PREFIX = "17700"

SURNAMES = list("王李张刘陈杨黄赵周吴徐孙马朱胡林何郭高")
GIVEN = ["雅婷", "美玲", "志强", "建国", "晓峰", "婷婷", "俊杰", "秀英",
         "浩然", "梓涵", "欣怡", "文博", "casey", "静", "磊", "洋"]

SERVICES = ["剪发造型", "头皮护理", "染发", "烫发", "美甲", "面部护理",
            "SPA 芳疗", "会员储值", "产品购买", "接发"]
STAFF = ["Tony", "Kevin", "小美", "阿杰", "Luna"]
PAYMENTS = ["微信", "支付宝", "会员卡", "现金"]
FEEDBACKS = [
    "服务很满意，下次还来", "对染发颜色比较挑剔，需注意沟通",
    "带朋友一起来的", "反馈价格略高", "很喜欢新发型",
    "对头皮护理效果满意", "临时改约过一次", "",
]
GENDERS = ["male", "female", "female", "female"]  # 偏女性,贴近美业
CONTACTS = ["wechat", "sms", "wechat", "wechat"]

# 客户画像：控制到店节奏，制造高/中/低风险分布
# (标签, 到店次数区间, 距今天数区间-最近一次, 客单价区间, 频率天数)
PROFILES = [
    ("高价值忠实", (12, 20), (1, 10), (280, 520), (14, 22)),
    ("稳定常客",   (6, 12),  (5, 20), (160, 320), (25, 40)),
    ("新客观察",   (1, 3),   (2, 25), (120, 300), (30, 60)),
    ("流失预警",   (4, 9),   (55, 110), (150, 340), (20, 35)),
    ("沉睡客户",   (2, 6),   (95, 180), (100, 260), (30, 50)),
]


def rand_name() -> str:
    return random.choice(SURNAMES) + random.choice(GIVEN)


def build_visits(store_id: str, customer_id: str, profile) -> list[Visit]:
    _, visit_range, recency_range, price_range, freq_days = profile
    n = random.randint(*visit_range)
    last_gap = random.randint(*recency_range)
    # 最近一次到店时间
    cursor = datetime.utcnow() - timedelta(days=last_gap)
    visits: list[Visit] = []
    for _ in range(n):
        amount = round(random.uniform(*price_range), 2)
        visits.append(Visit(
            id=uuid.uuid4().hex,
            customer_id=customer_id,
            store_id=store_id,
            visited_at=cursor,
            service_type=random.choice(SERVICES),
            staff_name=random.choice(STAFF),
            amount=amount,
            payment_method=random.choice(PAYMENTS),
            feedback=random.choice(FEEDBACKS) or None,
            source="manual",
        ))
        # 往更早的时间回退一个到店间隔
        gap = random.randint(freq_days[0], freq_days[1])
        cursor = cursor - timedelta(days=gap)
    return visits


def score_from_visits(visits: list[Visit]) -> tuple[float, float, str, dict]:
    """用最近度/频率/趋势近似算流失分与 CLV（和前端维度口径一致）。"""
    now = datetime.utcnow()
    ordered = sorted(visits, key=lambda v: v.visited_at, reverse=True)
    total = len(ordered)
    days_ago = (now - ordered[0].visited_at).days
    active_days = max(1, (now - ordered[-1].visited_at).days)
    monthly_freq = total / max(1, active_days / 30)

    # 最近度评分（越久没来分越低 = 越可能流失）
    recency = max(0, 100 - days_ago * 1.1)
    # 频率评分
    frequency = min(100, monthly_freq * 45)
    # 趋势评分：近半消费 vs 前半消费
    half = max(1, total // 2)
    recent_avg = sum(float(v.amount) for v in ordered[:half]) / half
    earlier = ordered[half:] or ordered[:half]
    earlier_avg = sum(float(v.amount) for v in earlier) / len(earlier)
    change = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg else 0
    trend = max(0, min(100, 50 + change))

    health = recency * 0.4 + frequency * 0.3 + trend * 0.3
    churn = round(max(2, min(98, 100 - health)), 1)

    total_spend = sum(float(v.amount) for v in ordered)
    clv = round(total_spend * (1.6 + frequency / 120), 2)

    if churn > 60:
        rec = "流失风险较高，建议尽快通过专属优惠或回访唤回。"
    elif churn >= 30:
        rec = "状态平稳，可用会员权益或新服务提升粘性。"
    else:
        rec = "高粘性客户，适合做转介绍与储值升级。"

    dims = {
        "recency_score": round(recency),
        "frequency_score": round(frequency),
        "trend_score": round(trend),
        "total_visits": total,
        "days_ago": days_ago,
    }
    return churn, clv, rec, dims


async def main() -> None:
    session_factory = get_session_factory()
    async with session_factory() as db:
        # 找到测试商家的店铺
        user = (await db.execute(
            select(User).where(User.phone == MERCHANT_PHONE)
        )).scalar_one_or_none()
        if user is None:
            raise RuntimeError(
                f"未找到手机号 {MERCHANT_PHONE} 的用户，请先运行 seed_test_accounts.py"
            )
        store = (await db.execute(
            select(Store).where(Store.owner_id == user.id)
        )).scalars().first()
        if store is None:
            raise RuntimeError("该用户名下没有店铺，请先完成 Onboarding 或运行 seed_test_accounts.py")

        store_id = store.id

        # 幂等：清掉旧的演示客户（按手机号前缀）
        old = (await db.execute(
            select(Customer).where(
                Customer.store_id == store_id,
                Customer.phone.like(f"{DEMO_PHONE_PREFIX}%"),
            )
        )).scalars().all()
        for c in old:
            await db.delete(c)  # 级联删除 visits / ai_metric
        if old:
            await db.flush()
            print(f"cleared {len(old)} existing demo customers")

        created = 0
        for i in range(DEMO_COUNT):
            profile = PROFILES[i % len(PROFILES)]
            cid = uuid.uuid4().hex
            phone = f"{DEMO_PHONE_PREFIX}{random.randint(100000, 999999)}"
            gender = random.choice(GENDERS)
            customer = Customer(
                id=cid,
                store_id=store_id,
                name=rand_name(),
                phone=phone,
                email=None,
                gender=gender,
                birthday=None,
                address=random.choice(["", "", "市中心店", "分店A"]) or None,
                preferred_contact=random.choice(CONTACTS),
                consent_status="granted",
            )
            db.add(customer)

            visits = build_visits(store_id, cid, profile)
            for v in visits:
                db.add(v)

            churn, clv, rec, _dims = score_from_visits(visits)
            db.add(AiMetric(
                id=uuid.uuid4().hex,
                customer_id=cid,
                store_id=store_id,
                churn_score=churn,
                clv=clv,
                recommendation=rec,
                computed_at=datetime.utcnow(),
            ))
            created += 1

        await db.commit()
        print(f"seeded {created} demo customers into store {store_id}")


if __name__ == "__main__":
    asyncio.run(main())
