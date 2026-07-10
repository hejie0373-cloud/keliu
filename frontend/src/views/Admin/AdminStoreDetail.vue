<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/http'
import * as billingApi from '@/api/billing'
import type { PaymentOrder } from '@/api/billing'

const route = useRoute()
const storeId = route.params.id as string

const store = ref<any>(null)
const orders = ref<PaymentOrder[]>([])
const loading = ref(true)
const saving = ref(false)
const ordersLoading = ref(false)
const orderTotal = ref(0)
const restrictionSaving = ref(false)
const restrictions = reactive({ ai: false, campaign: false, export: false })

const subForm = reactive({ planName: 'free', status: 'active', customerLimit: 1000, nextBillingDate: null as string | null })
const planOpts = [
  { value: 'free', label: '免费版' }, { value: 'basic', label: '基础版 ¥19.9' }, { value: 'professional', label: '专业版 ¥49.9' },
]
const statusOpts = [
  { value: 'active', label: '已激活' }, { value: 'overdue', label: '已过期' }, { value: 'cancelled', label: '已取消' },
]
const statusLabels: Record<string, string> = { pending: '待支付', paid: '已支付', failed: '失败', cancelled: '取消', expired: '过期' }
function money(c: number) { return `¥${(c / 100).toFixed(2)}` }
function stag(v: string) {
  if (v === 'paid' || v === 'active') return 'tag-ok'
  if (v === 'pending' || v === 'trial') return 'tag-warn'
  if (v === 'failed' || v === 'overdue') return 'tag-bad'
  return 'tag-dim'
}
function formatTime(value: string | null) {
  if (!value) return '-'
  const d = new Date(value + 'Z')
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function fillSub(sub: any) {
  subForm.planName = sub?.planName || sub?.plan || 'free'; subForm.status = sub?.status || 'active'
  subForm.customerLimit = sub?.customerLimit || 1000; subForm.nextBillingDate = sub?.nextBillingDate || null
  const restr = (sub?.restrictions || '').split(',').filter(Boolean)
  restrictions.ai = restr.includes('ai'); restrictions.campaign = restr.includes('campaign'); restrictions.export = restr.includes('export')
}

async function saveRestrictions() {
  restrictionSaving.value = true
  try {
    const list = []; if (restrictions.ai) list.push('ai'); if (restrictions.campaign) list.push('campaign'); if (restrictions.export) list.push('export')
    await http.put(`/admin/stores/${storeId}/restrictions`, null, { params: { restrictions: list.join(',') } })
    ElMessage.success('限制已更新'); await loadStore()
  } finally { restrictionSaving.value = false }
}
async function loadStore() { const { data } = await http.get(`/admin/stores/${storeId}`); store.value = data; fillSub(data.subscription) }
async function loadOrders() {
  ordersLoading.value = true
  try { const { data } = await billingApi.listStoreOrders(storeId, { page: 1, pageSize: 10 }); orders.value = data.items; orderTotal.value = data.total } finally { ordersLoading.value = false }
}
async function reload() { loading.value = true; try { await Promise.all([loadStore(), loadOrders()]) } finally { loading.value = false } }
async function toggleUser(uid: string) { await http.put(`/admin/users/${uid}/toggle`); ElMessage.success('用户状态已切换'); await loadStore() }
async function deleteUser(uid: string, name: string) {
  await ElMessageBox.confirm(`确定删除用户「${name}」？此操作不可恢复`, '删除用户', { type: 'warning', confirmButtonText: '删除' })
  await http.delete(`/admin/users/${uid}`); ElMessage.success('已删除'); await loadStore()
}
async function saveSub() {
  saving.value = true
  try {
    await billingApi.updateStoreSubscription(storeId, {
      planName: subForm.planName as any, status: subForm.status as any, customerLimit: subForm.customerLimit, nextBillingDate: subForm.nextBillingDate,
    })
    ElMessage.success('已更新'); await loadStore()
  } finally { saving.value = false }
}
async function handleRestrict() {
  if (!store.value) return
  const owner = store.value.owner; const staff = store.value.staff || []
  const allUsers = owner ? [owner, ...staff] : staff
  const activeCount = allUsers.filter((u: any) => u.isActive).length
  const action = activeCount > 0 ? '禁用后该店铺所有用户将无法登录和操作，确定继续？' : '启用后该店铺所有用户将恢复登录权限，确定继续？'
  await ElMessageBox.confirm(action, activeCount ? '禁用店铺' : '启用店铺', { type: 'warning', confirmButtonText: activeCount ? '确认禁用' : '确认启用', cancelButtonText: '取消' })
  await http.put(`/admin/stores/${storeId}/toggle`); ElMessage.success(activeCount ? '店铺已禁用' : '店铺已启用'); await loadStore()
}
function activeCount(list: any[]) { return list?.filter((u: any) => u.isActive)?.length || 0 }

onMounted(reload)
</script>

<template>
  <div class="admin-route page" v-loading="loading">
    <button class="back-link" @click="$router.push('/admin/stores')">← 返回店铺列表</button>

    <template v-if="store">
      <header class="hero-bar" v-reveal>
        <div class="hero-left">
          <div class="avatar">{{ store.name[0] }}</div>
          <div>
            <h1>{{ store.name }}</h1>
            <span class="hero-meta">{{ store.industryType || '未知行业' }} · {{ store.address || '未填地址' }} · 创建于 {{ store.createdAt?.slice(0,10) || '-' }}</span>
          </div>
        </div>
        <div class="hero-right">
          <span class="dot" :class="store.subscription?.isActive ? 'on' : 'off'" />
          {{ store.subscription?.isActive ? '正常运营' : '已停用' }}
        </div>
      </header>

      <div class="body-grid" v-reveal>
        <div class="col">
          <!-- Subscription -->
          <section class="card">
            <h3 class="card-title">订阅管理</h3>
            <div class="fg"><label>套餐</label><el-select v-model="subForm.planName" class="full-control"><el-option v-for="o in planOpts" :key="o.value" :label="o.label" :value="o.value" /></el-select></div>
            <div class="fg"><label>状态</label><el-select v-model="subForm.status" class="full-control"><el-option v-for="o in statusOpts" :key="o.value" :label="o.label" :value="o.value" /></el-select></div>
            <div class="fg"><label>客户上限</label><el-input-number v-model="subForm.customerLimit" :min="0" :max="99999" class="full-control" /></div>
            <div class="fg"><label>到期日期</label><el-date-picker v-model="subForm.nextBillingDate" type="date" value-format="YYYY-MM-DD" class="full-control" /></div>
            <button class="btn-primary" :disabled="saving" @click="saveSub">{{ saving ? '保存中...' : '保存订阅' }}</button>
          </section>

          <!-- Restrictions -->
          <section class="card">
            <div class="card-head">
              <h3 class="card-title">功能限制</h3>
              <button :class="['btn-sm', activeCount(store.staff) > 0 || store.owner?.isActive ? 'btn-danger' : 'btn-ok']" @click="handleRestrict">
                {{ activeCount(store.staff) > 0 || store.owner?.isActive ? '禁用店铺' : '启用店铺' }}
              </button>
            </div>
            <p class="card-desc">禁用后该店铺所有人员将无法登录，客户数据保留。</p>
            <div class="rlist">
              <label :class="['rchip', { on: restrictions.ai }]"><input type="checkbox" v-model="restrictions.ai" /><span class="rcb" /><div><strong>AI 评分/文案</strong><small>禁止流失分析和文案生成</small></div></label>
              <label :class="['rchip', { on: restrictions.campaign }]"><input type="checkbox" v-model="restrictions.campaign" /><span class="rcb" /><div><strong>营销活动</strong><small>禁止创建和发送营销活动</small></div></label>
              <label :class="['rchip', { on: restrictions.export }]"><input type="checkbox" v-model="restrictions.export" /><span class="rcb" /><div><strong>数据导出</strong><small>禁止导出 CSV 文件</small></div></label>
            </div>
            <button class="btn-secondary restriction-save" :disabled="restrictionSaving" @click="saveRestrictions">{{ restrictionSaving ? '保存中...' : '保存限制' }}</button>

            <div class="user-section">
              <h4>店铺人员</h4>
              <div class="user-list">
                <div v-if="store.owner" class="user-row">
                  <div class="user-info"><div class="uav owner-av">{{ store.owner.name[0] }}</div><div><strong>{{ store.owner.name }}</strong><span>{{ store.owner.phone }}</span></div></div>
                  <div class="user-actions">
                    <span :class="['tag', store.owner.isActive ? 'tag-ok' : 'tag-bad']">{{ store.owner.isActive ? '正常' : '禁用' }}</span>
                    <span class="role-tag">店主</span>
                    <button class="minibtn" @click="toggleUser(store.owner.id)">{{ store.owner.isActive ? '禁用' : '启用' }}</button>
                  </div>
                </div>
                <div v-for="s in store.staff" :key="s.id" class="user-row">
                  <div class="user-info"><div class="uav staff-av">{{ s.name[0] }}</div><div><strong>{{ s.name }}</strong><span>{{ s.phone }}</span></div></div>
                  <div class="user-actions">
                    <span :class="['tag', s.isActive ? 'tag-ok' : 'tag-bad']">{{ s.isActive ? '正常' : '禁用' }}</span>
                    <button class="minibtn" @click="toggleUser(s.id)">{{ s.isActive ? '禁用' : '启用' }}</button>
                    <button class="minibtn del" @click="deleteUser(s.id, s.name)">删除</button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div class="col">
          <!-- Customers -->
          <section class="card">
            <h3 class="card-title">客户列表 · {{ store.customerCount }} 人</h3>
            <div v-for="c in store.customers?.slice(0, 20)" :key="c.id" class="cust-row"><span class="cn">{{ c.name }}</span><span class="cm">{{ c.phone }} · {{ c.gender === 'male' ? '男' : '女' }}</span></div>
            <p v-if="store.customerCount > 20" class="more">... 还有 {{ store.customerCount - 20 }} 位客户</p>
          </section>

          <!-- Orders -->
          <section class="card">
            <div class="card-head"><h3 class="card-title">支付历史 · {{ orderTotal }} 条</h3><button class="minibtn" @click="loadOrders">刷新</button></div>
            <div class="mini-table-wrap">
              <table class="mini-table"><thead><tr><th>套餐</th><th>金额</th><th>状态</th><th>时间</th></tr></thead>
                <tbody>
                  <tr v-for="o in orders" :key="o.id"><td>{{ planOpts.find(p => p.value === o.planName)?.label || o.planName }}</td><td class="mono">{{ money(o.amountCents) }}</td><td><span :class="['tag', stag(o.status)]">{{ statusLabels[o.status] || o.status }}</span></td><td class="mono time">{{ formatTime(o.createdAt) }}</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { padding: 16px 24px 40px; }
.back-link { display: inline-block; background: none; border: none; color: var(--admin-text-secondary); font-size: 0.84rem; cursor: pointer; padding: 0; margin-bottom: 14px; transition: color 0.15s; }
.back-link:hover { color: var(--admin-accent); }

/* Hero */
.hero-bar { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; margin-bottom: 18px; background: var(--admin-surface); border: 1px solid var(--admin-border); border-radius: 8px; }
.hero-left { display: flex; align-items: center; gap: 14px; }
.avatar { width: 44px; height: 44px; border-radius: 10px; background: var(--admin-accent); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; font-weight: 800; }
.hero-bar h1 { margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--admin-text); }
.hero-meta { font-size: 0.78rem; color: var(--admin-text-secondary); }
.hero-right { display: flex; align-items: center; gap: 8px; font-size: 0.84rem; color: var(--admin-text-secondary); }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.on { background: var(--admin-green); }
.dot.off { background: var(--admin-red); }

/* Grid */
.body-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; align-items: start; }
@media (max-width: 860px) { .body-grid { grid-template-columns: 1fr; } }
.col { display: flex; flex-direction: column; gap: 14px; }

/* Card */
.card { background: var(--admin-surface); border: 1px solid var(--admin-border); border-radius: 8px; padding: 18px 20px; }
.card-title { margin: 0 0 16px; font-size: 0.9rem; font-weight: 700; color: var(--admin-text); }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.card-head .card-title { margin-bottom: 0; }
.card-desc { margin: 0 0 14px; font-size: 0.78rem; color: var(--admin-text-secondary); }

/* Forms */
.fg { margin-bottom: 12px; }
.fg label { display: block; margin-bottom: 5px; font-size: 0.74rem; font-weight: 700; color: var(--admin-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
.full-control { width: 100%; }

/* Buttons */
.btn-primary { width: 100%; padding: 10px; border: none; border-radius: 6px; background: var(--admin-accent); color: #fff; font-size: 0.86rem; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.btn-primary:hover { background: color-mix(in srgb, var(--admin-accent) 78%, #000); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }
.btn-secondary { padding: 8px 14px; border: 1px solid var(--admin-border); border-radius: 6px; background: var(--admin-surface); color: var(--admin-text-secondary); font-size: 0.82rem; cursor: pointer; transition: all 0.15s; }
.btn-secondary:hover { border-color: var(--admin-accent); color: var(--admin-accent); }
.btn-sm { padding: 4px 12px; border-radius: 4px; border: 1px solid; font-size: 0.74rem; font-weight: 600; cursor: pointer; transition: all 0.15s; background: transparent; }
.btn-danger { border-color: var(--admin-red-light); color: var(--admin-red); }
.btn-danger:hover { background: var(--admin-red-light); }
.btn-ok { border-color: var(--admin-green-light); color: var(--admin-green); }
.btn-ok:hover { background: var(--admin-green-light); }

/* Tags */
.tag { display: inline-flex; padding: 2px 10px; border-radius: 3px; font-size: 0.72rem; font-weight: 600; }
.tag-ok { background: var(--admin-green-light); color: var(--admin-green); }
.tag-warn { background: var(--admin-amber-light); color: var(--admin-amber); }
.tag-bad { background: var(--admin-red-light); color: var(--admin-red); }
.tag-dim { background: color-mix(in srgb, var(--admin-accent-light) 22%, var(--admin-surface)); color: var(--admin-text-secondary); }
.role-tag { font-size: 0.7rem; color: var(--admin-accent); background: var(--admin-accent-light); padding: 1px 8px; border-radius: 3px; font-weight: 600; }

/* Users */
.user-section { margin-top: 20px; border-top: 1px solid var(--admin-border); padding-top: 14px; }
.user-section h4 { margin: 0 0 10px; font-size: 0.8rem; font-weight: 700; color: var(--admin-text-secondary); }
.user-row { display: flex; align-items: center; justify-content: space-between; padding: 11px 0; border-bottom: 1px solid var(--admin-border); gap: 12px; }
.user-row:last-child { border-bottom: none; }
.user-info { display: flex; align-items: center; gap: 10px; min-width: 0; }
.uav { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.76rem; font-weight: 700; flex-shrink: 0; }
.owner-av { background: var(--admin-accent-light); color: var(--admin-accent); }
.staff-av { background: color-mix(in srgb, var(--admin-accent-light) 22%, var(--admin-surface)); color: var(--admin-text-secondary); }
.user-info strong { display: block; font-size: 0.84rem; color: var(--admin-text); }
.user-info span { font-size: 0.74rem; color: var(--admin-text-secondary); }
.user-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.minibtn { padding: 3px 10px; border: 1px solid var(--admin-border); border-radius: 4px; background: var(--admin-surface); color: var(--admin-text-secondary); font-size: 0.72rem; cursor: pointer; transition: all 0.15s; }
.minibtn:hover { border-color: var(--admin-accent); color: var(--admin-accent); }
.minibtn.del:hover { border-color: var(--admin-red); color: var(--admin-red); }

/* Restrict */
.rlist { display: flex; flex-direction: column; gap: 8px; margin-bottom: 4px; }
.restriction-save { width: 100%; margin-top: 12px; }
.rchip { display: flex; align-items: flex-start; gap: 12px; padding: 10px 14px; border: 1px solid var(--admin-border); border-radius: 8px; cursor: pointer; transition: all 0.15s; }
.rchip:hover { border-color: var(--admin-text-secondary); background: color-mix(in srgb, var(--admin-accent-light) 16%, var(--admin-surface)); }
.rchip.on { border-color: var(--admin-red); background: var(--admin-red-light); }
.rchip input { display: none; }
.rcb { width: 20px; height: 20px; border-radius: 5px; border: 2px solid var(--admin-border); flex-shrink: 0; transition: all 0.15s; display: flex; align-items: center; justify-content: center; }
.rchip.on .rcb { border-color: var(--admin-red); background: var(--admin-red); }
.rchip.on .rcb::after { content: '✕'; color: #fff; font-size: 11px; font-weight: 700; }
.rchip strong { display: block; font-size: 0.84rem; color: var(--admin-text); }
.rchip small { display: block; font-size: 0.74rem; color: var(--admin-text-secondary); margin-top: 2px; }
.rchip.on strong { color: var(--admin-red); }

/* Customers */
.cust-row { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid var(--admin-border); }
.cust-row:last-child { border-bottom: none; }
.cn { font-weight: 600; font-size: 0.84rem; color: var(--admin-text); }
.cm { font-size: 0.78rem; color: var(--admin-text-secondary); }
.more { text-align: center; font-size: 0.8rem; color: var(--admin-text-secondary); padding-top: 8px; margin: 0; }

/* Mini table */
.mini-table-wrap { border-radius: 6px; overflow: hidden; }
.mini-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.mini-table thead { background: color-mix(in srgb, var(--admin-accent-light) 28%, var(--admin-surface)); }
.mini-table th { padding: 8px 10px; text-align: left; font-size: 0.7rem; font-weight: 700; color: var(--admin-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--admin-border); }
.mini-table td { padding: 7px 10px; border-bottom: 1px solid var(--admin-border); color: var(--admin-text); }
.mini-table tr:last-child td { border-bottom: none; }
.mini-table tbody tr:hover { background: color-mix(in srgb, var(--admin-accent-light) 20%, var(--admin-surface)); }
.mono { font-family: 'SF Mono','Cascadia Code','Consolas',monospace; font-size: 0.74rem; }
.time { color: var(--admin-text-secondary); }

@media (max-width: 640px) {
  .page { padding: 12px 12px 32px; }
  .hero-bar { flex-direction: column; align-items: flex-start; gap: 10px; }
  .user-row { flex-direction: column; align-items: flex-start; }
  .user-actions { flex-wrap: wrap; }
}
</style>
