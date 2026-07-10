<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import http from '@/api/http'
import { importCSV, getImportProgress } from '@/api/customers'
import * as billingApi from '@/api/billing'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const step = ref<number>(1)
const loading = ref(false)
const isStepOne = computed(() => step.value === 1)
const isStepTwo = computed(() => step.value === 2)
const isStepThree = computed(() => step.value === 3)

const storeForm = ref({ name: '', address: '', industryType: '' })
const industries = ['餐饮', '美容美发', '零售', '健身', '其他']

async function createStore() {
  if (!storeForm.value.name.trim()) {
    ElMessage.warning('请输入店铺名称')
    return
  }
  loading.value = true
  try {
    await http.post('/stores', {
      name: storeForm.value.name,
      address: storeForm.value.address,
      industryType: storeForm.value.industryType,
    })
    await auth.fetchMe()
    step.value = 2
  } finally {
    loading.value = false
  }
}

const plans = [
  { id: 'basic', name: '基础版', price: 9.9, customers: 500, desc: '适合初创小店' },
  { id: 'professional', name: '专业版', price: 39.9, customers: 2000, desc: '适合成长型店铺', recommended: true },
  { id: 'enterprise', name: '旗舰版', price: 59.9, customers: 10000, desc: '适合连锁店铺' },
]
const selectedPlan = ref('professional')

async function selectPlan() {
  loading.value = true
  try {
    const { data: order } = await billingApi.createOrder(selectedPlan.value, 'mock')
    await billingApi.mockPay(order.id)
    ElMessage.success('套餐已开通')
    step.value = 3
  } finally {
    loading.value = false
  }
}

const uploading = ref(false)
const importDone = ref(false)

async function handleFile(file: File) {
  uploading.value = true
  try {
    const { data } = await importCSV(file)
    const timer = window.setInterval(async () => {
      const { data: prog } = await getImportProgress(data.taskId)
      if (prog.status === 'done' || prog.status === 'error') {
        clearInterval(timer)
        uploading.value = false
        importDone.value = true
        ElMessage.success(`导入完成: ${prog.success} 条`)
      }
    }, 2000)
  } catch {
    uploading.value = false
  }
}

function finish() {
  router.push('/dashboard')
}

onMounted(() => {
  const saved = localStorage.getItem('onboarding_step')
  if (saved) step.value = Number.parseInt(saved, 10)
})
</script>
<template>
  <div class="onboarding-page">
    <header class="onboarding-hero" v-reveal>
      <span class="hero-kicker">新店引导</span>
      <h1>把店铺、套餐和第一批客户准备好。</h1>
      <p>三步完成基础配置，进入仪表盘后可以继续补充客户资料和营销动作。</p>
    </header>

    <el-steps :active="step - 1" align-center class="onboarding-steps">
      <el-step title="店铺信息" />
      <el-step title="选择套餐" />
      <el-step title="导入客户" />
    </el-steps>

    <div v-if="isStepOne" class="card onboarding-card" v-reveal>
      <h2>创建你的店铺</h2>
      <p class="card-desc">新店铺默认有 5 次免费体验，用完后再选择套餐付费。</p>
      <el-form label-position="top">
        <el-form-item label="店铺名称" required>
          <el-input v-model="storeForm.name" placeholder="例如：张老板美容美发" size="large" />
        </el-form-item>
        <el-form-item label="行业类型">
          <el-select v-model="storeForm.industryType" placeholder="选择行业" size="large" class="full-select">
            <el-option v-for="ind in industries" :key="ind" :label="ind" :value="ind" />
          </el-select>
        </el-form-item>
        <el-form-item label="店铺地址">
          <el-input v-model="storeForm.address" placeholder="可选" size="large" />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" class="full-btn" @click="createStore">
          下一步
        </el-button>
      </el-form>
    </div>

    <div v-if="isStepTwo" class="plan-section" v-reveal>
      <h2>选择套餐</h2>
      <div class="plan-grid">
        <div
          v-for="p in plans"
          :key="p.id"
          :class="['plan-card', { selected: selectedPlan === p.id, recommended: p.recommended }]"
          @click="selectedPlan = p.id"
        >
          <div v-if="p.recommended" class="plan-badge">推荐</div>
          <div class="plan-name">{{ p.name }}</div>
          <div class="plan-price">¥{{ p.price }}<span>/月</span></div>
          <div class="plan-desc">{{ p.desc }}</div>
          <div class="plan-limit">最多 {{ p.customers }} 位客户</div>
        </div>
      </div>
      <el-button type="primary" size="large" :loading="loading" class="full-btn plan-submit" @click="selectPlan">
        模拟支付并开通
      </el-button>
    </div>

    <div v-if="isStepThree" class="card onboarding-card import-card" v-reveal>
      <h2>导入第一批客户</h2>
      <p class="card-desc">上传 CSV 文件，或跳过稍后导入。</p>

      <div v-if="!importDone" class="upload-shell">
        <el-upload drag :auto-upload="false" accept=".csv" :show-file-list="false" :on-change="(f: any) => handleFile(f.raw)">
          <div class="upload-inner">
            <p class="upload-icon">CSV</p>
            <p v-if="!uploading">拖拽 CSV 到此处或点击上传</p>
            <p v-else>导入中...</p>
          </div>
        </el-upload>
      </div>
      <div v-else class="import-done">导入完成</div>

      <div class="finish-actions">
        <el-button size="large" @click="finish">跳过</el-button>
        <el-button type="primary" size="large" @click="finish">进入仪表盘</el-button>
      </div>
    </div>
  </div>
</template>
<style scoped>
.onboarding-page {
  width: min(760px, 100%);
  margin: 0 auto;
  padding: 42px 24px 48px;
}

.onboarding-hero {
  margin-bottom: 24px;
  text-align: center;
}

.hero-kicker {
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 800;
}

.onboarding-hero h1,
.onboarding-card h2,
.plan-section h2 {
  margin: 8px 0 0;
  color: var(--ink);
  letter-spacing: 0;
}

.onboarding-hero h1 {
  font-size: 1.55rem;
}

.onboarding-hero p,
.card-desc {
  color: var(--ink-muted);
  line-height: 1.6;
}

.onboarding-hero p {
  margin: 10px auto 0;
  max-width: 560px;
}

.onboarding-steps {
  margin-bottom: 28px;
}

.onboarding-card {
  padding: 26px;
  border-radius: 8px;
  text-align: left;
}

.onboarding-card h2,
.plan-section h2 {
  margin-bottom: 8px;
  font-size: 1.15rem;
}

.card-desc {
  margin: 0 0 24px;
}

.full-btn {
  width: 100%;
}

.full-select {
  width: 100%;
}

.plan-section {
  text-align: center;
}

.plan-section h2 {
  margin-bottom: 24px;
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.plan-card {
  background: var(--surface);
  border: 2px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}
.plan-card:hover { border-color: var(--accent); }
.plan-card.selected { border-color: var(--accent); background: var(--accent-light); }
.plan-card.recommended { border-color: var(--accent); }
.plan-badge {
  position: absolute; top: -10px; right: 16px;
  background: var(--accent); color: var(--accent-contrast); padding: 2px 12px; border-radius: 100px; font-size: 0.8rem; font-weight: 600;
}
.plan-name { font-size: 1rem; font-weight: 700; margin-bottom: 8px; }
.plan-price { font-size: 2rem; font-weight: 700; color: var(--accent); }
.plan-price span {
  color: var(--ink-muted);
  font-size: 0.9rem;
}
.plan-desc { font-size: 0.85rem; color: var(--ink-muted); margin-top: 4px; }
.plan-limit {
  color: var(--ink-muted);
  font-size: 0.85rem;
  margin-top: 8px;
}
.plan-submit {
  margin-top: 24px;
}

.import-card {
  text-align: center;
}

.upload-shell {
  margin-bottom: 16px;
  padding: 32px;
  border: 2px dashed var(--border);
  border-radius: 8px;
  background: var(--surface-2);
}

.upload-inner {
  padding: 24px;
}

.upload-icon {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 2rem;
  font-weight: 800;
}

.import-done {
  padding: 24px;
  color: var(--success);
  font-size: 1.1rem;
  font-weight: 700;
}

.finish-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 720px) {
  .plan-grid {
    grid-template-columns: 1fr;
  }
}
</style>




