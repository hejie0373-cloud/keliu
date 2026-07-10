<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'
import { getDashboard } from '@/api/analytics'
import type { DashboardData } from '@/types/analytics'
import StatCard from '@/components/common/StatCard.vue'
import { revealStagger, tweenWidth, prefersReducedMotion } from '@/utils/motion'
import VChart from 'vue-echarts'
import * as echarts from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import { TooltipComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, PieChart, TooltipComponent, GridComponent, CanvasRenderer])

const router = useRouter()
const notif = useNotificationStore()
const data = ref<DashboardData | null>(null)
const loading = ref(true)

// Stripe 风调色板
const C = {
  brand:   '#635BFF',
  brand2:  '#7A73FF',
  coral:   '#FF7A59',
  mint:    '#10B981',
  amber:   '#F59E0B',
  red:     '#EF4444',
  ink:     '#1A1F36',
  muted:   '#8792A2',
  light:   '#F6F9FC',
}

const metricsRoot = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    const { data: res } = await getDashboard({ silentError: true })
    data.value = res
  } catch { /* */ }
  finally {
    loading.value = false
    // 指标区进场 + 风险条填充在下一帧触发（DOM 就绪后）
    requestAnimationFrame(() => {
      if (metricsRoot.value) {
        revealStagger(Array.from(metricsRoot.value.children) as HTMLElement[])
      }
      document.querySelectorAll<HTMLElement>('.risk-bar-fill').forEach((el, i) => {
        const pct = Number(el.dataset.pct || 0)
        tweenWidth(el, pct, { delay: 0.3 + i * 0.08 })
      })
    })
  }
})

// 到店趋势用于迷你 sparkline
const trendSpark = computed(() => data.value?.visitTrend?.map((p) => p.count) || [])

// 趋势面积图，带绘制动画
const trendOption = computed(() => ({
  animationDuration: prefersReducedMotion() ? 0 : 1100,
  animationEasing: 'cubicOut' as const,
  tooltip: {
    trigger: 'axis' as const,
    backgroundColor: '#fff',
    borderColor: '#E6E9F0',
    textStyle: { color: C.ink, fontSize: 13 },
    formatter: (params: any) => {
      const p = params[0]
      return `<b>${p.axisValue}</b><br/>到店 <b style="color:${C.brand}">${p.value}</b> 人次`
    },
  },
  grid: { left: 16, right: 16, top: 16, bottom: 8, containLabel: true },
  xAxis: {
    type: 'category' as const,
    boundaryGap: false,
    data: data.value?.visitTrend?.map((p) => p.date.slice(5)) || [],
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: C.muted, fontSize: 12 },
  },
  yAxis: {
    type: 'value' as const,
    minInterval: 1,
    splitLine: { lineStyle: { color: '#EEF1F6', type: 'dashed' as const } },
    axisLabel: { color: C.muted, fontSize: 12 },
  },
  series: [{
    data: data.value?.visitTrend?.map((p) => p.count) || [],
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 7,
    showSymbol: false,
    lineStyle: { color: C.brand, width: 3 },
    itemStyle: { color: C.brand, borderColor: '#fff', borderWidth: 2 },
    areaStyle: {
      color: {
        type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(99,91,255,0.20)' },
          { offset: 1, color: 'rgba(99,91,255,0.01)' },
        ],
      },
    },
  }],
}))

// 风险分布环形图
const churnPieOption = computed(() => {
  const d = data.value?.churnDistribution
  if (!d) return {}
  return {
    animationDuration: prefersReducedMotion() ? 0 : 900,
    tooltip: { trigger: 'item' as const, backgroundColor: '#fff', borderColor: '#E6E9F0', textStyle: { color: C.ink } },
    series: [{
      type: 'pie',
      radius: ['58%', '82%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 3 },
      label: { show: false },
      emphasis: { scale: true, scaleSize: 4, label: { show: true, fontSize: 15, fontWeight: 'bold' } },
      data: [
        { value: d.high, name: '高风险', itemStyle: { color: C.red } },
        { value: d.medium, name: '中风险', itemStyle: { color: C.amber } },
        { value: d.low, name: '低风险', itemStyle: { color: C.mint } },
      ],
    }],
  }
})

function riskLevel(score: number) {
  if (score > 60) return 'high'
  if (score >= 30) return 'medium'
  return 'low'
}

const churnTotal = computed(() => {
  const d = data.value?.churnDistribution
  return d ? d.high + d.medium + d.low : 0
})
</script>

<template>
  <div class="dashboard-shell">
    <header class="dashboard-hero">
      <div class="hero-copy">
        <span class="hero-kicker">经营总览</span>
        <h1>快速看见今天的客户状态。</h1>
        <p>把客户数量、流失风险、到店趋势和高价值客户放在同一个视图里，减少切换成本。</p>
      </div>

      <el-popover placement="bottom-end" :width="320" trigger="click">
        <template #reference>
          <el-badge :value="notif.unreadCount" :hidden="notif.unreadCount === 0">
            <button class="notice-btn" type="button">🔔</button>
          </el-badge>
        </template>
        <p v-if="!notif.messages.length" class="notice-empty">暂无通知</p>
        <div v-else class="notice-list">
          <div v-for="(msg, i) in notif.messages.slice(0, 10)" :key="i" class="notice-item">
            <span v-if="msg.type === 'high_risk_alert'" class="notice-tag notice-tag--danger">高风险预警</span>
            <span v-else class="notice-tag">系统通知</span>
          </div>
          <el-button text size="small" class="notice-read" @click="notif.markAllRead()">全部已读</el-button>
        </div>
      </el-popover>
    </header>

    <el-skeleton :loading="loading" animated :count="4">
      <template v-if="data">
        <section ref="metricsRoot" class="metric-grid">
          <StatCard
            label="总客户"
            :value="data.totalCustomers"
            note="当前在库客户总量"
            tone="accent"
            :spark="trendSpark"
          />
          <StatCard
            label="高风险"
            :value="data.highRiskCount"
            note="需要优先跟进"
            tone="danger"
            clickable
            @click="router.push('/customers?risk=high')"
          />
          <StatCard
            label="高价值"
            :value="data.highValueCount"
            note="值得做复购与转介绍"
            tone="success"
          />
          <StatCard
            label="今日到店"
            :value="data.todayVisits"
            note="今天新增到店次数"
            tone="warning"
          />
        </section>

        <section class="content-grid">
          <article class="panel panel--wide">
            <div class="panel-head">
              <div>
                <h3>到店趋势</h3>
                <p>近 7 天到店人次</p>
              </div>
              <span class="panel-chip">
                {{ (data.visitTrend || []).reduce((s: number, p: any) => s + p.count, 0) }} 人次
              </span>
            </div>
            <v-chart v-if="data.visitTrend?.length" :option="trendOption" class="chart chart--line" autoresize />
            <div v-else class="panel-empty">暂无到店数据</div>
          </article>

          <article class="panel">
            <div class="panel-head">
              <div>
                <h3>流失风险</h3>
                <p>最近一次评分分布</p>
              </div>
            </div>
            <div v-if="churnTotal" class="pie-wrap">
              <v-chart :option="churnPieOption" class="chart chart--pie" autoresize />
              <div class="pie-center">
                <strong>{{ churnTotal }}</strong>
                <span>已评分</span>
              </div>
            </div>
            <div v-else class="panel-empty">暂无评分数据</div>
          </article>

          <article class="panel panel--list">
            <div class="panel-head">
              <div>
                <h3>高风险客户</h3>
                <p>优先处理的前 5 位</p>
              </div>
              <router-link to="/customers" class="panel-link">全部查看 →</router-link>
            </div>
            <div v-if="!data.topRiskCustomers?.length" class="panel-empty">暂无高风险客户</div>
            <button
              v-for="c in data.topRiskCustomers"
              :key="c.id"
              class="risk-row"
              type="button"
              @click="router.push(`/customers/${c.id}`)"
            >
              <div class="risk-avatar" :class="`risk-${riskLevel(c.churnScore)}`">{{ c.name[0] }}</div>
              <div class="risk-body">
                <div class="risk-name">{{ c.name }}</div>
                <div class="risk-phone">{{ c.phone }}</div>
              </div>
              <div class="risk-score-wrap">
                <div class="risk-bar-bg">
                  <div
                    class="risk-bar-fill"
                    :class="`risk-${riskLevel(c.churnScore)}`"
                    :data-pct="c.churnScore"
                    style="width:0%"
                  />
                </div>
                <span class="risk-val" :class="`text-${riskLevel(c.churnScore)}`">{{ c.churnScore }}</span>
              </div>
            </button>
          </article>
        </section>
      </template>
    </el-skeleton>
  </div>
</template>

<style scoped>
.dashboard-shell {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard-hero {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 28px 26px 26px;
  border-radius: var(--radius-lg);
  background:
    radial-gradient(120% 140% at 0% 0%, rgba(99, 91, 255, 0.10), transparent 60%),
    radial-gradient(120% 140% at 100% 0%, rgba(255, 122, 89, 0.08), transparent 55%),
    var(--surface);
  border: 1px solid var(--border);
  overflow: hidden;
}

.hero-copy { min-width: 0; }

.hero-kicker {
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.dashboard-hero h1 {
  margin: 8px 0 0;
  font-size: 1.55rem;
  line-height: 1.2;
  color: var(--ink);
}

.dashboard-hero p {
  max-width: 620px;
  margin: 10px 0 0;
  color: var(--ink-muted);
}

.notice-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  font-size: 1.05rem;
  flex-shrink: 0;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
.notice-btn:hover { box-shadow: var(--shadow-md); border-color: var(--accent-light); }

.notice-empty { padding: 12px; color: var(--ink-muted); }
.notice-list { display: flex; flex-direction: column; gap: 8px; }
.notice-item { padding: 8px 0; border-bottom: 1px solid var(--border); }
.notice-tag {
  display: inline-flex; padding: 3px 8px; border-radius: 999px;
  background: var(--bg); color: var(--ink); font-size: 0.78rem;
}
.notice-tag--danger { background: var(--danger-light); color: var(--danger); }
.notice-read { width: 100%; margin-top: 8px; }

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1.8fr 1fr 1.1fr;
  gap: 16px;
}

.panel {
  min-height: 340px;
  padding: 22px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.panel-head h3 { margin: 0; color: var(--ink); font-size: 1rem; }
.panel-head p { margin: 4px 0 0; color: var(--ink-muted); font-size: 0.8rem; }

.panel-chip {
  flex-shrink: 0;
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--accent-light);
  color: var(--accent-hover);
  font-size: 0.78rem;
  font-weight: 700;
}

.panel-link { color: var(--accent); font-size: 0.82rem; text-decoration: none; }
.panel-link:hover { text-decoration: underline; }

.panel-empty {
  display: flex; align-items: center; justify-content: center;
  min-height: 240px; color: var(--ink-muted); font-size: 0.9rem;
}

.chart { width: 100%; }
.chart--line { height: 288px; }
.chart--pie { height: 260px; }

.pie-wrap { position: relative; }
.pie-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  pointer-events: none;
}
.pie-center strong { font-size: 1.8rem; font-weight: 800; color: var(--ink); font-variant-numeric: tabular-nums; }
.pie-center span { font-size: 0.78rem; color: var(--ink-muted); margin-top: 2px; }

.risk-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 8px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
}
.risk-row:hover { background: var(--bg); }

.risk-avatar {
  width: 38px; height: 38px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 0.9rem; font-weight: 700; flex-shrink: 0;
}
.risk-avatar.risk-high { background: var(--risk-high); }
.risk-avatar.risk-medium { background: var(--risk-medium); }
.risk-avatar.risk-low { background: var(--risk-low); }

.risk-body { flex: 1; min-width: 0; }
.risk-name { color: var(--ink); font-size: 0.9rem; font-weight: 700; }
.risk-phone { color: var(--ink-muted); font-size: 0.78rem; }

.risk-score-wrap { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.risk-bar-bg { width: 62px; height: 6px; border-radius: 999px; background: var(--bg); overflow: hidden; }
.risk-bar-fill { height: 100%; border-radius: 999px; }
.risk-bar-fill.risk-high { background: var(--risk-high); }
.risk-bar-fill.risk-medium { background: var(--risk-medium); }
.risk-bar-fill.risk-low { background: var(--risk-low); }

.risk-val { width: 28px; font-size: 0.85rem; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }
.text-high { color: var(--risk-high); }
.text-medium { color: var(--risk-medium); }
.text-low { color: var(--risk-low); }

@media (max-width: 1180px) {
  .metric-grid, .content-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .panel--wide, .panel--list { grid-column: span 2; }
}

@media (max-width: 720px) {
  .metric-grid, .content-grid { grid-template-columns: 1fr; }
  .panel--wide, .panel--list { grid-column: span 1; }
}
</style>
