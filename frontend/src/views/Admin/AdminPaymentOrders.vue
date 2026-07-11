<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as billingApi from '@/api/billing'
import type { AdminPaymentSummary, PaymentOrder } from '@/api/billing'

const orders = ref<PaymentOrder[]>([])
const summary = ref<AdminPaymentSummary | null>(null)
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref('')

const statusOptions = [
  { value: '', label: '全部' },
  { value: 'pending', label: '待支付' },
  { value: 'paid', label: '已支付' },
  { value: 'failed', label: '失败' },
  { value: 'cancelled', label: '取消' },
  { value: 'expired', label: '过期' },
]
const planLabels: Record<string, string> = { basic: '基础版', professional: '专业版', enterprise: '旗舰版' }
const statusLabels: Record<string, string> = { pending: '待支付', paid: '已支付', failed: '失败', cancelled: '取消', expired: '过期' }
function money(c: number) { return `¥${(c / 100).toFixed(2)}` }
function stag(v: string) {
  if (v === 'paid') return 'tag-ok'
  if (v === 'pending') return 'tag-warn'
  if (v === 'failed' || v === 'cancelled') return 'tag-bad'
  return 'tag-dim'
}
function formatTime(value: string | null) {
  if (!value) return '-'
  const d = new Date(value + 'Z')
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}
function formatDist(counts?: Record<string, number>) {
  if (!counts || Object.keys(counts).length === 0) return '-'
  return Object.entries(counts).map(([k, c]) => `${planLabels[k] || k} ${c}`).join(' · ')
}

async function loadSummary() { const { data } = await billingApi.getAdminPaymentSummary(); summary.value = data }
async function loadOrders() {
  loading.value = true
  try {
    const { data } = await billingApi.listAdminOrders({ page: page.value, pageSize, status: status.value || undefined })
    orders.value = data.items; total.value = data.total
  } finally { loading.value = false }
}
function onStatusChange() { page.value = 1; loadOrders() }
function onPage(n: number) { page.value = n; loadOrders() }

onMounted(async () => { await Promise.all([loadSummary(), loadOrders()]) })
</script>

<template>
  <div class="admin-route page">
    <header class="hero" v-reveal>
      <div>
        <h1>支付订单</h1>
        <p>查看平台收入、订单状态和商家支付记录 · 共 {{ total }} 条</p>
      </div>
      <button class="refresh-btn" @click="loadOrders">刷新</button>
    </header>

    <div class="summary-strip" v-reveal>
      <div class="sum-item"><span class="sum-label">今日收入</span><strong class="sum-val">{{ money(summary?.todayRevenueCents || 0) }}</strong></div>
      <div class="sum-div" />
      <div class="sum-item"><span class="sum-label">本月收入</span><strong class="sum-val">{{ money(summary?.monthRevenueCents || 0) }}</strong></div>
      <div class="sum-div" />
      <div class="sum-item"><span class="sum-label">已支付</span><strong class="sum-val green">{{ summary?.paidOrders || 0 }}</strong></div>
      <div class="sum-div" />
      <div class="sum-item"><span class="sum-label">待支付</span><strong class="sum-val amber">{{ summary?.pendingOrders || 0 }}</strong></div>
      <div class="sum-div" />
      <div class="sum-item sum-wide"><span class="sum-label">套餐分布</span><span class="sum-dist">{{ formatDist(summary?.planCounts) }}</span></div>
    </div>

    <div class="filter-bar" v-reveal>
      <button v-for="o in statusOptions" :key="o.value" :class="['chip', { active: status === o.value }]" @click="status = o.value; onStatusChange()">{{ o.label }}</button>
    </div>

    <div class="table-wrap" v-reveal>
      <table>
        <thead><tr><th>订单号</th><th>店铺</th><th>套餐</th><th>金额</th><th>渠道</th><th>状态</th><th>支付时间</th><th>创建时间</th></tr></thead>
        <tbody>
          <tr v-for="row in orders" :key="row.id">
            <td class="mono">{{ row.id.slice(0, 12) }}...</td>
            <td>{{ row.storeName || row.storeId.slice(0, 10) + '...' }}</td>
            <td>{{ planLabels[row.planName] || row.planName }}</td>
            <td class="mono">{{ money(row.amountCents) }}</td>
            <td>{{ row.provider === 'mock' ? '模拟' : row.provider === 'alipay' ? '支付宝' : row.provider }}</td>
            <td><span :class="['tag', stag(row.status)]">{{ statusLabels[row.status] || row.status }}</span></td>
            <td class="mono time">{{ formatTime(row.paidAt) }}</td>
            <td class="mono time">{{ formatTime(row.createdAt) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="orders.length === 0 && !loading" class="empty">暂无订单记录</div>
    </div>

    <div class="pager" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="onPage(page - 1)">上一页</button>
      <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <button :disabled="page >= Math.ceil(total / pageSize)" @click="onPage(page + 1)">下一页</button>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 16px 24px 40px; }
.hero { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.hero h1 { font-size: 1.35rem; font-weight: 700; color: var(--admin-text); margin: 0; }
.hero p { color: var(--admin-text-secondary); font-size: 0.85rem; margin: 4px 0 0; }
.refresh-btn { padding: 6px 16px; border: 1px solid var(--admin-border); border-radius: 6px; background: var(--admin-surface); color: var(--admin-text-secondary); font-size: 0.82rem; cursor: pointer; transition: all 0.15s; }
.refresh-btn:hover { border-color: var(--admin-accent); color: var(--admin-accent); }

.summary-strip { display: flex; align-items: center; gap: 0; padding: 14px 18px; margin-bottom: 14px; background: var(--admin-surface); border: 1px solid var(--admin-border); border-radius: 8px; }
.sum-item { padding: 0 18px; }
.sum-div { width: 1px; height: 28px; background: var(--admin-border); }
.sum-label { display: block; font-size: 0.68rem; font-weight: 700; color: var(--admin-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 2px; }
.sum-val { font-size: 1.1rem; font-weight: 800; color: var(--admin-text); }
.sum-val.green { color: var(--admin-green); }
.sum-val.amber { color: var(--admin-amber); }
.sum-wide { flex: 1; }
.sum-dist { font-size: 0.82rem; color: var(--admin-text); }

.filter-bar { display: flex; gap: 6px; margin-bottom: 14px; }
.chip { padding: 5px 14px; border: 1px solid var(--admin-border); border-radius: 4px; background: var(--admin-surface); color: var(--admin-text-secondary); font-size: 0.78rem; cursor: pointer; transition: all 0.15s; }
.chip:hover { border-color: var(--admin-text-secondary); }
.chip.active { border-color: var(--admin-accent); background: var(--admin-accent-light); color: var(--admin-accent); font-weight: 600; }

.table-wrap { background: var(--admin-surface); border: 1px solid var(--admin-border); border-radius: 8px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
thead { background: color-mix(in srgb, var(--admin-accent-light) 28%, var(--admin-surface)); }
th { padding: 10px 14px; text-align: left; font-size: 0.71rem; font-weight: 700; color: var(--admin-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--admin-border); }
td { padding: 10px 14px; border-bottom: 1px solid var(--admin-border); color: var(--admin-text); }
tr:last-child td { border-bottom: none; }
tbody tr:hover { background: color-mix(in srgb, var(--admin-accent-light) 20%, var(--admin-surface)); }
.mono { font-family: 'SF Mono','Cascadia Code','Consolas',monospace; font-size: 0.78rem; }
.time { color: var(--admin-text-secondary); }

.tag { display: inline-flex; padding: 2px 10px; border-radius: 3px; font-size: 0.72rem; font-weight: 600; }
.tag-ok { background: var(--admin-green-light); color: var(--admin-green); }
.tag-warn { background: var(--admin-amber-light); color: var(--admin-amber); }
.tag-bad { background: var(--admin-red-light); color: var(--admin-red); }
.tag-dim { background: color-mix(in srgb, var(--admin-accent-light) 22%, var(--admin-surface)); color: var(--admin-text-secondary); }

.empty { padding: 40px; text-align: center; color: var(--admin-text-secondary); }
.pager { display: flex; align-items: center; justify-content: center; gap: 16px; padding-top: 16px; }
.pager button { padding: 6px 14px; border: 1px solid var(--admin-border); border-radius: 6px; background: var(--admin-surface); color: var(--admin-text-secondary); font-size: 0.82rem; cursor: pointer; }
.pager button:hover:not(:disabled) { border-color: var(--admin-accent); color: var(--admin-accent); }
.pager button:disabled { opacity: 0.4; cursor: default; }
.pager span { font-size: 0.82rem; color: var(--admin-text-secondary); }

@media (max-width: 800px) {
  .page { padding: 12px 12px 32px; }
  .summary-strip { flex-wrap: wrap; gap: 8px; }
  .sum-div { display: none; }
  .table-wrap { overflow-x: auto; }
}
</style>
