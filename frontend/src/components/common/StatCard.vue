<script setup lang="ts">
/**
 * StatCard — Stripe 风格指标卡
 *
 * 特性：
 * - 顶部彩色强调条（by tone）
 * - 大号渐变数字，进场滚动（AnimatedNumber）
 * - 可选迷你趋势 sparkline（纯 SVG，无依赖）
 * - hover 微浮起 + 阴影加深
 * - 可点击（clickable），点击 emit('click')
 * - reduced-motion 下动效自动降级
 */
import { computed } from 'vue'
import AnimatedNumber from './AnimatedNumber.vue'
import { liftIn, liftOut } from '@/utils/motion'

type Tone = 'accent' | 'danger' | 'success' | 'warning' | 'neutral'

const props = withDefaults(defineProps<{
  label: string
  value: number
  note?: string
  tone?: Tone
  prefix?: string
  suffix?: string
  decimals?: number
  /** 迷你趋势数据（可选） */
  spark?: number[]
  clickable?: boolean
  /** 进场延迟，配合父级 stagger */
  delay?: number
}>(), {
  tone: 'neutral',
  decimals: 0,
  delay: 0,
})

const emit = defineEmits<{ (e: 'click'): void }>()

// 迷你趋势 SVG 路径
const sparkPath = computed(() => {
  const data = props.spark
  if (!data || data.length < 2) return ''
  const w = 100
  const h = 32
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const step = w / (data.length - 1)
  return data
    .map((v, i) => {
      const x = i * step
      const y = h - ((v - min) / range) * h
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const sparkArea = computed(() => {
  if (!sparkPath.value) return ''
  return `${sparkPath.value} L100,32 L0,32 Z`
})

function onEnter(e: MouseEvent) {
  liftIn(e.currentTarget as Element)
}
function onLeave(e: MouseEvent) {
  liftOut(e.currentTarget as Element)
}
function onClick() {
  if (props.clickable) emit('click')
}
</script>

<template>
  <component
    :is="clickable ? 'button' : 'article'"
    class="stat-card"
    :class="[`stat-card--${tone}`, { 'stat-card--clickable': clickable }]"
    :style="{ '--delay': `${delay}s` }"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
    @click="onClick"
  >
    <span class="stat-card__bar" />
    <div class="stat-card__head">
      <span class="stat-card__label">{{ label }}</span>
      <slot name="badge" />
    </div>

    <div class="stat-card__value-row">
      <AnimatedNumber
        class="stat-card__value"
        :value="value"
        :prefix="prefix"
        :suffix="suffix"
        :decimals="decimals"
        :delay="delay + 0.1"
      />
      <svg
        v-if="sparkPath"
        class="stat-card__spark"
        viewBox="0 0 100 32"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path class="stat-card__spark-area" :d="sparkArea" />
        <path class="stat-card__spark-line" :d="sparkPath" />
      </svg>
    </div>

    <span v-if="note" class="stat-card__note">{{ note }}</span>
    <slot />
  </component>
</template>

<style scoped>
.stat-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 140px;
  padding: 20px 22px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  text-align: left;
  font-family: inherit;
  transition: box-shadow 0.25s ease, border-color 0.25s ease;
}

.stat-card--clickable {
  cursor: pointer;
}

.stat-card:hover {
  box-shadow: var(--shadow-lg);
  border-color: var(--accent-light);
}

/* 顶部彩色强调条 */
.stat-card__bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.stat-card--accent .stat-card__bar { background: linear-gradient(90deg, var(--accent), var(--accent-hover)); }
.stat-card--danger .stat-card__bar { background: var(--danger); }
.stat-card--success .stat-card__bar { background: var(--success); }
.stat-card--warning .stat-card__bar { background: var(--warning); }
.stat-card--neutral .stat-card__bar { background: var(--border); }

.stat-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.stat-card__label {
  color: var(--ink-muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.stat-card__value-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
}

.stat-card__value {
  font-size: 2.1rem;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

/* tone 决定大数字的渐变 */
.stat-card--accent .stat-card__value {
  background: linear-gradient(135deg, var(--accent), var(--accent-hover));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.stat-card--danger .stat-card__value { color: var(--danger); }
.stat-card--success .stat-card__value { color: var(--success); }
.stat-card--warning .stat-card__value { color: var(--warning); }
.stat-card--neutral .stat-card__value { color: var(--ink); }

.stat-card__spark {
  width: 96px;
  height: 32px;
  flex-shrink: 0;
}

.stat-card__spark-line {
  fill: none;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.stat-card__spark-area {
  opacity: 0.14;
}

.stat-card--accent .stat-card__spark-line { stroke: var(--accent); }
.stat-card--accent .stat-card__spark-area { fill: var(--accent); }
.stat-card--danger .stat-card__spark-line { stroke: var(--danger); }
.stat-card--danger .stat-card__spark-area { fill: var(--danger); }
.stat-card--success .stat-card__spark-line { stroke: var(--success); }
.stat-card--success .stat-card__spark-area { fill: var(--success); }
.stat-card--warning .stat-card__spark-line { stroke: var(--warning); }
.stat-card--warning .stat-card__spark-area { fill: var(--warning); }
.stat-card--neutral .stat-card__spark-line { stroke: var(--ink-muted); }
.stat-card--neutral .stat-card__spark-area { fill: var(--ink-muted); }

.stat-card__note {
  color: var(--ink-muted);
  font-size: 0.8rem;
  margin-top: 2px;
}
</style>
