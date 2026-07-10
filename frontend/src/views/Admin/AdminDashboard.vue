<script setup lang="ts">
import { ref, onMounted } from 'vue'
import http, { getApiErrorMessage } from '@/api/http'

interface Overview {
  totalStores: number; totalUsers: number; activeUsers: number
  totalCustomers: number; highRiskCustomers: number
  activeStores: number; todayNewCustomers: number
  todayRevenueCents: number; monthRevenueCents: number
  paidOrders: number; pendingOrders: number; failedOrders: number
  planDistribution: Record<string, number>
  subscriptionStatus: Record<string, number>
  todayVisits: number
  totalCampaigns: number; activeCampaigns: number
}

const overview = ref<Overview | null>(null)
const error = ref('')

function money(c: number) { return `¥${(c / 100).toFixed(2)}` }
const planLabels: Record<string, string> = { free: '免费版', basic: '基础版', professional: '专业版' }
const planColors: Record<string, string> = {
  free: 'var(--admin-teal)',
  basic: 'var(--admin-accent)',
  professional: 'var(--admin-purple)',
}
const statusLabels: Record<string, string> = { active: '活跃', overdue: '过期', cancelled: '取消' }

onMounted(async () => {
  try {
    const { data } = await http.get('/admin/overview')
    overview.value = data as any
  } catch (e) {
    error.value = getApiErrorMessage(e, '加载失败')
  }
})
</script>

<template>
  <div class="admin-route dash">
    <div v-if="error" class="err-msg">{{ error }}</div>

    <template v-if="overview">
      <header class="hero" v-reveal>
        <h1>平台总览</h1>
        <p>实时监控平台运营数据：商家规模、营收流水、客户增长、订阅分布</p>
      </header>

      <!-- Row 1: 核心指标 -->
      <div class="kpi-row" v-reveal>
        <div class="kpi">
          <div class="kpi-icon kpi-icon--blue">◆</div>
          <div class="kpi-body">
            <span class="kpi-label">总店铺</span>
            <strong class="kpi-value">{{ overview.totalStores }}</strong>
            <span class="kpi-sub">活跃 {{ overview.activeStores }}</span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon kpi-icon--purple">◆</div>
          <div class="kpi-body">
            <span class="kpi-label">平台用户</span>
            <strong class="kpi-value">{{ overview.totalUsers }}</strong>
            <span class="kpi-sub">活跃 {{ overview.activeUsers }}</span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon kpi-icon--green">◆</div>
          <div class="kpi-body">
            <span class="kpi-label">客户总数</span>
            <strong class="kpi-value">{{ overview.totalCustomers }}</strong>
            <span class="kpi-sub">今日 +{{ overview.todayNewCustomers }}</span>
          </div>
        </div>
        <div class="kpi kpi--warn">
          <div class="kpi-icon kpi-icon--amber">!</div>
          <div class="kpi-body">
            <span class="kpi-label">高风险客户</span>
            <strong class="kpi-value">{{ overview.highRiskCustomers }}</strong>
            <span class="kpi-sub">流失分 &gt; 60</span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon kpi-icon--blue">￥</div>
          <div class="kpi-body">
            <span class="kpi-label">今日营收</span>
            <strong class="kpi-value">{{ money(overview.todayRevenueCents) }}</strong>
            <span class="kpi-sub">本月 {{ money(overview.monthRevenueCents) }}</span>
          </div>
        </div>
      </div>

      <!-- Row 2: 订单 + 今日动态 -->
      <div class="grid-2" v-reveal>
        <!-- 订单状态 -->
        <div class="card">
          <h3 class="card-title">支付订单</h3>
          <div class="order-stats">
            <div class="order-stat paid">
              <strong>{{ overview.paidOrders }}</strong>
              <span>已支付</span>
            </div>
            <div class="order-stat pending">
              <strong>{{ overview.pendingOrders }}</strong>
              <span>待支付</span>
            </div>
            <div class="order-stat failed">
              <strong>{{ overview.failedOrders }}</strong>
              <span>失败/取消</span>
            </div>
          </div>
        </div>

        <!-- 今日动态 -->
        <div class="card">
          <h3 class="card-title">今日动态</h3>
          <div class="today-list">
            <div class="today-item">
              <span class="today-dot green"></span>
              <div>
                <strong>{{ overview.todayNewCustomers }}</strong>
                <span>新增客户</span>
              </div>
            </div>
            <div class="today-item">
              <span class="today-dot blue"></span>
              <div>
                <strong>{{ overview.todayVisits }}</strong>
                <span>到店记录</span>
              </div>
            </div>
            <div class="today-item">
              <span class="today-dot amber"></span>
              <div>
                <strong>{{ money(overview.todayRevenueCents) }}</strong>
                <span>支付收入</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Row 3: 套餐分布 + 营销 -->
      <div class="grid-2" v-reveal>
        <!-- 套餐与订阅 -->
        <div class="card">
          <h3 class="card-title">套餐与订阅</h3>
          <div class="plan-section">
            <div class="plan-bars" v-if="Object.keys(overview.planDistribution).length">
              <div v-for="(count, plan) in overview.planDistribution" :key="plan" class="plan-row">
                <span class="plan-name">{{ planLabels[plan] || plan }}</span>
                <div class="plan-track">
                  <div class="plan-fill" :style="{ width: Math.max(count / overview.totalStores * 100, 4) + '%', background: planColors[plan] || 'var(--admin-accent)' }" />
                </div>
                <span class="plan-num">{{ count }} 家</span>
              </div>
            </div>
            <div v-if="Object.keys(overview.subscriptionStatus).length" class="sub-status">
              <span v-for="(count, status) in overview.subscriptionStatus" :key="status" class="sub-tag">
                {{ statusLabels[status] || status }} {{ count }}
              </span>
            </div>
          </div>
        </div>

        <!-- 营销活动 -->
        <div class="card">
          <h3 class="card-title">平台运营</h3>
          <div class="ops-grid">
            <div class="ops-item">
              <strong>{{ overview.totalCampaigns }}</strong>
              <span>营销活动</span>
              <small>已发送 {{ overview.activeCampaigns }}</small>
            </div>
            <div class="ops-item">
              <strong>{{ overview.totalCustomers }}</strong>
              <span>平台客户</span>
              <small>分布在 {{ overview.activeStores }} 家店铺</small>
            </div>
            <div class="ops-item">
              <strong>{{ overview.todayVisits }}</strong>
              <span>今日到店</span>
              <small>全平台到店记录</small>
            </div>
            <div class="ops-item">
              <strong>{{ overview.highRiskCustomers }}</strong>
              <span>需跟进客户</span>
              <small>高风险流失预警</small>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dash {
  padding: 16px 24px 32px;
  min-height: 200px;
}
.err-msg {
  padding: 48px; text-align: center; color: var(--admin-red); font-size: 0.95rem;
}

/* Hero */
.hero { margin-bottom: 20px; }
.hero h1 { font-size: 1.35rem; font-weight: 700; color: var(--admin-text); margin: 0; }
.hero p { color: var(--admin-text-secondary); font-size: 0.85rem; margin: 4px 0 0; }

/* KPI Row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.kpi {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 18px 18px;
  background: var(--admin-surface);
  border: 1px solid var(--admin-border);
  border-radius: 8px;
  transition: box-shadow 0.15s, border-color 0.15s, transform 0.15s;
}
.kpi:hover { border-color: var(--admin-accent); box-shadow: 0 8px 22px rgb(15 23 42 / 0.08); transform: translateY(-1px); }
.kpi--warn { border-left: 3px solid var(--admin-amber); }
.kpi-icon {
  width: 38px; height: 38px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 800; flex-shrink: 0;
}
.kpi-icon--blue { background: var(--admin-accent-light); color: var(--admin-accent); }
.kpi-icon--purple { background: var(--admin-purple-light); color: var(--admin-purple); }
.kpi-icon--green { background: var(--admin-green-light); color: var(--admin-green); }
.kpi-icon--amber { background: var(--admin-amber-light); color: var(--admin-amber); }
.kpi-body { display: flex; flex-direction: column; min-width: 0; }
.kpi-label { font-size: 0.73rem; font-weight: 600; color: var(--admin-text-secondary); }
.kpi-value { font-size: 1.45rem; font-weight: 800; color: var(--admin-text); line-height: 1.2; margin: 2px 0; }
.kpi-sub { font-size: 0.7rem; color: var(--admin-text-secondary); }

/* Grid */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }

/* Card */
.card {
  background: var(--admin-surface);
  border: 1px solid var(--admin-border);
  border-radius: 8px; padding: 18px 20px;
}
.card-title { margin: 0 0 16px; font-size: 0.88rem; font-weight: 700; color: var(--admin-text); }

/* Order stats */
.order-stats { display: flex; gap: 0; }
.order-stat {
  flex: 1; text-align: center; padding: 14px 8px;
  border-right: 1px solid var(--admin-border);
}
.order-stat:last-child { border-right: none; }
.order-stat strong { display: block; font-size: 1.6rem; font-weight: 800; line-height: 1; }
.order-stat span { display: block; font-size: 0.74rem; color: var(--admin-text-secondary); margin-top: 4px; }
.order-stat.paid strong { color: var(--admin-green); }
.order-stat.pending strong { color: var(--admin-amber); }
.order-stat.failed strong { color: var(--admin-red); }

/* Today */
.today-list { display: flex; flex-direction: column; gap: 14px; }
.today-item { display: flex; align-items: center; gap: 12px; }
.today-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; margin-top: 2px; }
.today-dot.green { background: var(--admin-green); }
.today-dot.blue { background: var(--admin-accent); }
.today-dot.amber { background: var(--admin-amber); }
.today-item strong { display: block; font-size: 1.05rem; font-weight: 700; color: var(--admin-text); }
.today-item span { font-size: 0.76rem; color: var(--admin-text-secondary); }

/* Plan bars */
.plan-section { display: flex; flex-direction: column; gap: 14px; }
.plan-bars { display: flex; flex-direction: column; gap: 10px; }
.plan-row { display: flex; align-items: center; gap: 10px; }
.plan-name { font-size: 0.82rem; font-weight: 600; color: var(--admin-text); width: 60px; flex-shrink: 0; }
.plan-track { flex: 1; height: 8px; border-radius: 4px; background: var(--admin-border); overflow: hidden; }
.plan-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; min-width: 2px; }
.plan-num { font-size: 0.82rem; font-weight: 700; color: var(--admin-text); min-width: 36px; text-align: right; }
.sub-status { display: flex; gap: 8px; flex-wrap: wrap; }
.sub-tag {
  padding: 3px 10px; border-radius: 4px; font-size: 0.74rem; font-weight: 600;
  background: var(--admin-accent-light); color: var(--admin-accent);
}

/* Ops grid */
.ops-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.ops-item { text-align: center; padding: 12px 8px; background: color-mix(in srgb, var(--admin-accent-light) 38%, var(--admin-surface)); border-radius: 8px; }
.ops-item strong { display: block; font-size: 1.5rem; font-weight: 800; color: var(--admin-text); }
.ops-item span { display: block; font-size: 0.78rem; font-weight: 600; color: var(--admin-text-secondary); margin: 2px 0; }
.ops-item small { display: block; font-size: 0.7rem; color: var(--admin-text-secondary); opacity: 0.7; }

/* Responsive */
@media (max-width: 1100px) {
  .kpi-row { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 800px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .grid-2 { grid-template-columns: 1fr; }
}
@media (max-width: 520px) {
  .kpi-row { grid-template-columns: 1fr; }
  .ops-grid { grid-template-columns: 1fr; }
  .dash { padding: 12px 10px 24px; }
}
</style>
