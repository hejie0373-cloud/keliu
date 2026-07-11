<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/api/http'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const stores = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const search = ref('')
const loading = ref(false)

const restrictVisible = ref(false)
const restrictStoreId = ref('')
const restrictStoreName = ref('')
const restrictStoreActive = ref(true)
const restrictionSaving = ref(false)
const restrictions = reactive({ ai: false, campaign: false, export: false })

async function loadStores() {
  loading.value = true
  try {
    const { data } = await http.get('/admin/stores', { params: { search: search.value || undefined, page: page.value, page_size: pageSize } })
    stores.value = (data as any).items || []; total.value = (data as any).total || 0
  } finally { loading.value = false }
}
function openRestrict(row: any) {
  restrictStoreId.value = row.id; restrictStoreName.value = row.name
  restrictStoreActive.value = row?.subscription?.isActive ?? true
  const restr = (row.subscription?.restrictions || '').split(',').filter(Boolean)
  restrictions.ai = restr.includes('ai'); restrictions.campaign = restr.includes('campaign'); restrictions.export = restr.includes('export')
  restrictVisible.value = true
}
async function saveRestrictions() {
  restrictionSaving.value = true
  try {
    const list = []; if (restrictions.ai) list.push('ai'); if (restrictions.campaign) list.push('campaign'); if (restrictions.export) list.push('export')
    await http.put(`/admin/stores/${restrictStoreId.value}/restrictions`, null, { params: { restrictions: list.join(',') } })
    restrictVisible.value = false; await loadStores(); ElMessage.success('限制已保存')
  } finally { restrictionSaving.value = false }
}
async function toggleFullDisable() {
  const sid = restrictStoreId.value
  if (restrictStoreActive.value) {
    await ElMessageBox.confirm('将禁用该店铺所有人员登录并限制全部功能。确定？', '完全禁用', { type: 'warning', confirmButtonText: '确认禁用' })
    await http.put(`/admin/stores/${sid}/restrictions`, null, { params: { restrictions: 'ai,campaign,export' } })
    await http.put(`/admin/stores/${sid}/toggle`)
  } else {
    await http.put(`/admin/stores/${sid}/restrictions`, null, { params: { restrictions: '' } })
    await http.put(`/admin/stores/${sid}/toggle`)
  }
  restrictStoreActive.value = !restrictStoreActive.value; restrictVisible.value = false; await loadStores()
  ElMessage.success(restrictStoreActive.value ? '店铺已启用' : '店铺已完全禁用')
}
function restrictState(sub: any): string {
  if (!sub?.restrictions) return 'none'
  const list = sub.restrictions.split(',').filter(Boolean)
  if (list.length === 0) return 'none'; if (list.length >= 3) return 'full'; return 'partial'
}
function restrictLabel(s: string) { return { none: '无限制', partial: '部分限制', full: '已禁用' }[s] || s }
function rtag(s: string) { return { none: 'tag-ok', partial: 'tag-warn', full: 'tag-bad' }[s] || 'tag-ok' }
function planLabel(sub: any) { return sub?.planDisplayName || sub?.plan || '免费版' }

onMounted(() => loadStores())
watch([page, search], () => { if (search.value) page.value = 1; loadStores() })
</script>

<template>
  <div class="admin-route page">
    <header class="hero" v-reveal>
      <div>
        <h1>店铺管理</h1>
        <p>检索商家店铺、查看套餐状态，并对功能权限进行平台侧管控 · 共 {{ total }} 家</p>
      </div>
    </header>

    <div class="search-bar" v-reveal>
      <input v-model="search" placeholder="搜索店铺名、店主或手机号..." @keyup.enter="loadStores()" />
      <button class="search-btn" @click="loadStores()">搜索</button>
    </div>

    <div class="table-wrap" v-reveal>
      <table>
        <thead><tr><th>店铺</th><th>套餐</th><th>限制状态</th><th class="action-col">操作</th></tr></thead>
        <tbody>
          <tr v-for="row in stores" :key="row.id">
            <td>
              <strong class="store-name">{{ row.name }}</strong>
              <span class="store-owner">{{ row.ownerName || '未填店主' }} · {{ row.ownerPhone || '未填手机号' }}</span>
            </td>
            <td><span class="plan-badge">{{ planLabel(row.subscription) }}</span></td>
            <td><span :class="['tag', rtag(restrictState(row.subscription))]">{{ restrictLabel(restrictState(row.subscription)) }}</span></td>
            <td>
              <div class="actions">
                <button class="act-btn" @click="router.push(`/admin/stores/${row.id}`)">详情</button>
                <button class="act-btn warn" @click="openRestrict(row)">管控</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="stores.length === 0 && !loading" class="empty">暂无匹配店铺</div>
    </div>

    <div class="pager" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="page--">上一页</button>
      <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <button :disabled="page >= Math.ceil(total / pageSize)" @click="page++">下一页</button>
    </div>

    <el-dialog v-model="restrictVisible" :title="`店铺管控 · ${restrictStoreName}`" width="460px" destroy-on-close>
      <p class="dialog-desc">选择要限制的功能，勾选后商家端对应操作将被拦截。</p>
      <div class="restrict-list">
        <label :class="['rchip', { on: restrictions.ai }]">
          <input type="checkbox" v-model="restrictions.ai" /><span class="rcb" />
          <div><strong>AI 评分/文案</strong><small>禁止流失分析和文案生成</small></div>
        </label>
        <label :class="['rchip', { on: restrictions.campaign }]">
          <input type="checkbox" v-model="restrictions.campaign" /><span class="rcb" />
          <div><strong>营销活动</strong><small>禁止创建和发送营销活动</small></div>
        </label>
        <label :class="['rchip', { on: restrictions.export }]">
          <input type="checkbox" v-model="restrictions.export" /><span class="rcb" />
          <div><strong>数据导出</strong><small>禁止导出 CSV 文件</small></div>
        </label>
      </div>
      <el-button type="primary" :loading="restrictionSaving" class="full-btn" @click="saveRestrictions">保存限制</el-button>
      <el-divider />
      <div class="full-disable">
        <div>
          <strong>{{ restrictStoreActive ? '完全禁用店铺' : '重新启用店铺' }}</strong>
          <p>{{ restrictStoreActive ? '禁用所有人员登录，限制全部功能' : '恢复登录权限，清除所有限制' }}</p>
        </div>
        <el-button :type="restrictStoreActive ? 'danger' : 'success'" size="small" @click="toggleFullDisable">{{ restrictStoreActive ? '完全禁用' : '启用' }}</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { padding: 16px 24px 40px; }
.hero { margin-bottom: 16px; }
.hero h1 { font-size: 1.35rem; font-weight: 700; color: var(--admin-text); margin: 0; }
.hero p { color: var(--admin-text-secondary); font-size: 0.85rem; margin: 4px 0 0; }

.search-bar { display: flex; gap: 8px; margin-bottom: 14px; max-width: 500px; }
.search-bar input {
  flex: 1; padding: 8px 14px; border: 1px solid var(--admin-border); border-radius: 6px;
  font-size: 0.86rem; color: var(--admin-text); background: var(--admin-surface); outline: none;
  transition: border-color 0.15s;
}
.search-bar input::placeholder { color: color-mix(in srgb, var(--admin-text-secondary) 68%, transparent); }
.search-bar input:focus { border-color: var(--admin-accent); box-shadow: 0 0 0 3px var(--admin-accent-light); }
.search-btn {
  padding: 8px 18px; border: 1px solid var(--admin-accent); border-radius: 6px;
  background: var(--admin-accent); color: #fff; font-size: 0.84rem; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.search-btn:hover { background: color-mix(in srgb, var(--admin-accent) 78%, #000); }

.table-wrap { background: var(--admin-surface); border: 1px solid var(--admin-border); border-radius: 8px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
thead { background: color-mix(in srgb, var(--admin-accent-light) 28%, var(--admin-surface)); }
th { padding: 10px 14px; text-align: left; font-size: 0.71rem; font-weight: 700; color: var(--admin-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--admin-border); }
.action-col { width: 140px; }
td { padding: 10px 14px; border-bottom: 1px solid var(--admin-border); color: var(--admin-text); }
tr:last-child td { border-bottom: none; }
tbody tr:hover { background: color-mix(in srgb, var(--admin-accent-light) 20%, var(--admin-surface)); }
.store-name { display: block; font-size: 0.86rem; font-weight: 600; }
.store-owner { display: block; font-size: 0.76rem; color: var(--admin-text-secondary); margin-top: 2px; }
.plan-badge { display: inline-flex; padding: 2px 10px; border-radius: 4px; font-size: 0.74rem; font-weight: 600; background: var(--admin-accent-light); color: var(--admin-accent); }

.tag { display: inline-flex; padding: 2px 10px; border-radius: 3px; font-size: 0.72rem; font-weight: 600; }
.tag-ok { background: var(--admin-green-light); color: var(--admin-green); }
.tag-warn { background: var(--admin-amber-light); color: var(--admin-amber); }
.tag-bad { background: var(--admin-red-light); color: var(--admin-red); }

.actions { display: flex; gap: 8px; }
.act-btn { padding: 4px 12px; border: 1px solid var(--admin-border); border-radius: 4px; background: var(--admin-surface); color: var(--admin-text-secondary); font-size: 0.76rem; cursor: pointer; transition: all 0.15s; }
.act-btn:hover { border-color: var(--admin-accent); color: var(--admin-accent); }
.act-btn.warn:hover { border-color: var(--admin-amber); color: var(--admin-amber); }

.dialog-desc { color: var(--admin-text-secondary); font-size: 0.85rem; margin: 0 0 16px; }
.restrict-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 22px; }
.full-btn { width: 100%; }
.full-disable { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.full-disable strong { color: var(--admin-text); font-size: 0.9rem; }
.full-disable p { color: var(--admin-text-secondary); font-size: 0.8rem; margin: 2px 0 0; }
.rchip { display: flex; align-items: flex-start; gap: 12px; padding: 12px 14px; border: 1px solid var(--admin-border); border-radius: 8px; cursor: pointer; transition: all 0.15s; }
.rchip:hover { border-color: var(--admin-text-secondary); background: color-mix(in srgb, var(--admin-accent-light) 16%, var(--admin-surface)); }
.rchip.on { border-color: var(--admin-red); background: var(--admin-red-light); }
.rchip input { display: none; }
.rcb { width: 20px; height: 20px; border-radius: 5px; border: 2px solid var(--admin-border); flex-shrink: 0; transition: all 0.15s; display: flex; align-items: center; justify-content: center; }
.rchip.on .rcb { border-color: var(--admin-red); background: var(--admin-red); }
.rchip.on .rcb::after { content: '✕'; color: #fff; font-size: 11px; font-weight: 700; }
.rchip strong { display: block; font-size: 0.86rem; color: var(--admin-text); }
.rchip small { display: block; font-size: 0.74rem; color: var(--admin-text-secondary); margin-top: 2px; }
.rchip.on strong { color: var(--admin-red); }

.empty { padding: 40px; text-align: center; color: var(--admin-text-secondary); }
.pager { display: flex; align-items: center; justify-content: center; gap: 16px; padding-top: 16px; }
.pager button { padding: 6px 14px; border: 1px solid var(--admin-border); border-radius: 6px; background: var(--admin-surface); color: var(--admin-text-secondary); font-size: 0.82rem; cursor: pointer; }
.pager button:hover:not(:disabled) { border-color: var(--admin-accent); color: var(--admin-accent); }
.pager button:disabled { opacity: 0.4; cursor: default; }
.pager span { font-size: 0.82rem; color: var(--admin-text-secondary); }

@media (max-width: 640px) { .page { padding: 12px 12px 32px; } .table-wrap { overflow-x: auto; } }
</style>
