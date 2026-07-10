<script setup lang="ts">
/**
 * MemoryGraph — AI 记忆图谱（2D Canvas 力导向）
 *
 * 中心节点为客户，向外辐射「维度节点」：
 *   - 消费习惯（客单价 / 累计消费）
 *   - 服务偏好（最常用服务）
 *   - 到店频率
 *   - 风险信号（流失评分）
 *   - 关键时刻（最近若干次到店，作为叶子节点挂在「关键时刻」下）
 *
 * 交互：
 *   - 力导向自动布局（弹簧连线 + 节点斥力），节点轻微浮动呼吸
 *   - 悬停高亮，点击节点 -> emit('select', node) 供父级展开详情
 *   - 可拖拽节点，松手回弹到力导向平衡位
 *   - reduced-motion 下停用浮动/物理，直接静态布局
 *
 * 纯 Canvas，无第三方图库；数据来自真实 visits + aiMetric.dimensions。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { prefersReducedMotion } from '@/utils/motion'

interface Visit {
  id: string
  visitedAt: string
  serviceType?: string
  amount?: number | string
  staffName?: string
  paymentMethod?: string
  feedback?: string
}
interface Dimensions {
  recencyScore?: number
  frequencyScore?: number
  trendScore?: number
  totalVisits?: number
  daysAgo?: number
}

const props = defineProps<{
  name: string
  churnScore?: number | null
  clv?: number | null
  dimensions?: Dimensions | null
  visits?: Visit[]
}>()

const emit = defineEmits<{ (e: 'select', node: GraphNodeData): void }>()

export interface GraphNodeData {
  id: string
  kind: 'center' | 'dimension' | 'moment'
  title: string
  subtitle?: string
  tone: 'accent' | 'danger' | 'success' | 'warning' | 'neutral'
  detail?: Record<string, string>
}

interface PhysNode extends GraphNodeData {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  parent?: string
  phase: number // 呼吸相位
}
interface Edge { from: string; to: string; len: number }

const canvasRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLDivElement | null>(null)

let nodes: PhysNode[] = []
let edges: Edge[] = []
let raf = 0
let W = 0
let H = 0
let dpr = 1
let hoverId: string | null = null
let dragId: string | null = null
let dragDX = 0
let dragDY = 0
const reduced = prefersReducedMotion()

const TONE_COLOR: Record<GraphNodeData['tone'], string> = {
  accent: '#635BFF',
  danger: '#E5484D',
  success: '#10B981',
  warning: '#F5A623',
  neutral: '#8B90A0',
}

function num(v: unknown, d = 0): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number)
  return Number.isFinite(n) ? (n as number) : d
}

function riskTone(score: number | null | undefined): GraphNodeData['tone'] {
  if (score == null) return 'neutral'
  if (score > 60) return 'danger'
  if (score >= 30) return 'warning'
  return 'success'
}

/** 从真实数据构建图谱节点 */
const graphData = computed<{ nodes: GraphNodeData[]; edges: Edge[] }>(() => {
  const visits = props.visits || []
  const dims = props.dimensions || {}
  const ns: GraphNodeData[] = []
  const es: Edge[] = []

  ns.push({
    id: 'center',
    kind: 'center',
    title: props.name || '客户',
    subtitle: props.churnScore != null ? `流失分 ${Math.round(props.churnScore)}` : '未评分',
    tone: riskTone(props.churnScore),
  })

  // 消费习惯
  const amounts = visits.map((v) => num(v.amount)).filter((a) => a > 0)
  const total = amounts.reduce((s, a) => s + a, 0)
  const avg = amounts.length ? total / amounts.length : 0
  ns.push({
    id: 'spend',
    kind: 'dimension',
    title: '消费习惯',
    subtitle: avg ? `客单 ¥${avg.toFixed(0)}` : '暂无消费',
    tone: 'accent',
    detail: {
      客单价: avg ? `¥${avg.toFixed(0)}` : '—',
      累计消费: total ? `¥${total.toLocaleString()}` : '—',
      预估价值: props.clv != null ? `¥${Math.round(props.clv).toLocaleString()}` : '—',
    },
  })
  es.push({ from: 'center', to: 'spend', len: 120 })

  // 服务偏好
  const svcCount: Record<string, number> = {}
  visits.forEach((v) => {
    const s = v.serviceType || '到店服务'
    svcCount[s] = (svcCount[s] || 0) + 1
  })
  const topSvc = Object.entries(svcCount).sort((a, b) => b[1] - a[1])[0]
  ns.push({
    id: 'pref',
    kind: 'dimension',
    title: '服务偏好',
    subtitle: topSvc ? topSvc[0] : '暂无偏好',
    tone: 'success',
    detail: Object.fromEntries(
      Object.entries(svcCount).sort((a, b) => b[1] - a[1]).slice(0, 4)
        .map(([k, v]) => [k, `${v} 次`]),
    ),
  })
  es.push({ from: 'center', to: 'pref', len: 120 })

  // 到店频率
  ns.push({
    id: 'freq',
    kind: 'dimension',
    title: '到店频率',
    subtitle: `${num(dims.totalVisits, visits.length)} 次到店`,
    tone: 'warning',
    detail: {
      累计到店: `${num(dims.totalVisits, visits.length)} 次`,
      频率评分: `${num(dims.frequencyScore)} / 100`,
      距最近: dims.daysAgo != null ? `${dims.daysAgo} 天前` : '—',
    },
  })
  es.push({ from: 'center', to: 'freq', len: 120 })

  // 风险信号
  ns.push({
    id: 'risk',
    kind: 'dimension',
    title: '风险信号',
    subtitle: props.churnScore != null ? `${Math.round(props.churnScore)} 分` : '未评分',
    tone: riskTone(props.churnScore),
    detail: {
      流失评分: props.churnScore != null ? `${Math.round(props.churnScore)}` : '—',
      最近度: `${num(dims.recencyScore)} / 100`,
      消费趋势: `${num(dims.trendScore)} / 100`,
    },
  })
  es.push({ from: 'center', to: 'risk', len: 120 })

  // 关键时刻（最近 3 次到店挂在「风险信号」旁作为叶子）
  const recent = visits.slice(0, 3)
  recent.forEach((v, i) => {
    const id = `moment-${i}`
    ns.push({
      id,
      kind: 'moment',
      title: v.serviceType || '到店',
      subtitle: `¥${num(v.amount).toFixed(0)}`,
      tone: 'neutral',
      detail: {
        时间: v.visitedAt?.slice(0, 16).replace('T', ' ') || '—',
        金额: `¥${num(v.amount).toFixed(0)}`,
        员工: v.staffName || '—',
        反馈: v.feedback || '—',
      },
    })
    es.push({ from: 'freq', to: id, len: 66 })
  })

  return { nodes: ns, edges: es }
})

function radiusFor(kind: GraphNodeData['kind']): number {
  if (kind === 'center') return 42
  if (kind === 'dimension') return 30
  return 18
}

function initPhysics() {
  const { nodes: gn, edges: ge } = graphData.value
  const cx = W / 2
  const cy = H / 2
  nodes = gn.map((n, i) => {
    const angle = (i / Math.max(1, gn.length - 1)) * Math.PI * 2
    const dist = n.kind === 'center' ? 0 : n.kind === 'dimension' ? 120 : 170
    return {
      ...n,
      x: cx + Math.cos(angle) * dist + (Math.random() - 0.5) * 20,
      y: cy + Math.sin(angle) * dist + (Math.random() - 0.5) * 20,
      vx: 0,
      vy: 0,
      r: radiusFor(n.kind),
      phase: Math.random() * Math.PI * 2,
    }
  })
  edges = ge
}

function byId(id: string): PhysNode | undefined {
  return nodes.find((n) => n.id === id)
}

function step() {
  const cx = W / 2
  const cy = H / 2
  const center = byId('center')

  // 斥力（节点互斥）
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i]
      const b = nodes[j]
      let dx = a.x - b.x
      let dy = a.y - b.y
      let d2 = dx * dx + dy * dy
      if (d2 < 1) d2 = 1
      const d = Math.sqrt(d2)
      const min = a.r + b.r + 26
      const force = (2600 / d2)
      const ux = dx / d
      const uy = dy / d
      a.vx += ux * force
      a.vy += uy * force
      b.vx -= ux * force
      b.vy -= uy * force
      // 硬性防重叠
      if (d < min) {
        const push = (min - d) * 0.5
        a.vx += ux * push
        a.vy += uy * push
        b.vx -= ux * push
        b.vy -= uy * push
      }
    }
  }

  // 弹簧（连线拉力）
  for (const e of edges) {
    const a = byId(e.from)
    const b = byId(e.to)
    if (!a || !b) continue
    const dx = b.x - a.x
    const dy = b.y - a.y
    const d = Math.sqrt(dx * dx + dy * dy) || 1
    const diff = (d - e.len) * 0.02
    const ux = dx / d
    const uy = dy / d
    a.vx += ux * diff
    a.vy += uy * diff
    b.vx -= ux * diff
    b.vy -= uy * diff
  }

  // 中心锚定 + 阻尼 + 积分
  for (const n of nodes) {
    if (n.kind === 'center') {
      // 中心缓慢回到画布中央
      n.vx += (cx - n.x) * 0.02
      n.vy += (cy - n.y) * 0.02
    }
    if (n.id === dragId) {
      n.vx = 0
      n.vy = 0
      continue
    }
    n.vx *= 0.86
    n.vy *= 0.86
    n.x += n.vx
    n.y += n.vy
    // 边界约束
    n.x = Math.max(n.r + 4, Math.min(W - n.r - 4, n.x))
    n.y = Math.max(n.r + 4, Math.min(H - n.r - 4, n.y))
  }
  void center
}

function draw(t: number) {
  const ctx = canvasRef.value?.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, W, H)

  // 连线
  for (const e of edges) {
    const a = byId(e.from)
    const b = byId(e.to)
    if (!a || !b) continue
    const active = hoverId === a.id || hoverId === b.id
    // 呼吸透明度
    const breathe = reduced ? 0.5 : 0.35 + 0.18 * Math.sin(t / 700 + a.phase)
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.strokeStyle = active
      ? 'rgba(99,91,255,0.55)'
      : `rgba(140,144,160,${breathe.toFixed(3)})`
    ctx.lineWidth = active ? 2 : 1
    ctx.stroke()
  }

  // 节点
  for (const n of nodes) {
    const color = TONE_COLOR[n.tone]
    const isHover = hoverId === n.id
    const float = reduced ? 0 : Math.sin(t / 900 + n.phase) * 2
    const y = n.y + float
    const r = n.r + (isHover ? 3 : 0)

    // 光晕
    if (n.kind !== 'moment') {
      const grd = ctx.createRadialGradient(n.x, y, r * 0.4, n.x, y, r * 2.1)
      grd.addColorStop(0, hexA(color, isHover ? 0.42 : 0.26))
      grd.addColorStop(1, hexA(color, 0))
      ctx.fillStyle = grd
      ctx.beginPath()
      ctx.arc(n.x, y, r * 2.1, 0, Math.PI * 2)
      ctx.fill()
    }

    // 圆盘
    ctx.beginPath()
    ctx.arc(n.x, y, r, 0, Math.PI * 2)
    ctx.fillStyle = n.kind === 'center' ? color : '#ffffff'
    ctx.fill()
    ctx.lineWidth = n.kind === 'center' ? 0 : 2
    ctx.strokeStyle = color
    ctx.stroke()

    // 文本
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    if (n.kind === 'center') {
      ctx.fillStyle = '#fff'
      ctx.font = '700 15px system-ui, sans-serif'
      ctx.fillText(clip(n.title, 5), n.x, y - 6)
      ctx.font = '500 10px system-ui, sans-serif'
      ctx.fillStyle = 'rgba(255,255,255,0.85)'
      ctx.fillText(n.subtitle || '', n.x, y + 12)
    } else if (n.kind === 'dimension') {
      ctx.fillStyle = color
      ctx.font = '700 12px system-ui, sans-serif'
      ctx.fillText(clip(n.title, 4), n.x, y - 3)
      ctx.fillStyle = '#6b7280'
      ctx.font = '500 9px system-ui, sans-serif'
      ctx.fillText(clip(n.subtitle || '', 8), n.x, y + 11)
    } else {
      ctx.fillStyle = color
      ctx.font = '600 9px system-ui, sans-serif'
      ctx.fillText(clip(n.title, 4), n.x, y)
    }
  }
}

function hexA(hex: string, a: number): string {
  const h = hex.replace('#', '')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${a})`
}
function clip(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

function loop(t: number) {
  step()
  draw(t)
  raf = requestAnimationFrame(loop)
}

function resize() {
  const wrap = wrapRef.value
  const canvas = canvasRef.value
  if (!wrap || !canvas) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  W = wrap.clientWidth
  H = wrap.clientHeight
  canvas.width = W * dpr
  canvas.height = H * dpr
  canvas.style.width = `${W}px`
  canvas.style.height = `${H}px`
  const ctx = canvas.getContext('2d')
  ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function pickAt(px: number, py: number): PhysNode | null {
  // 从上层（后画的）往回找
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i]
    const dx = px - n.x
    const dy = py - n.y
    if (dx * dx + dy * dy <= (n.r + 4) * (n.r + 4)) return n
  }
  return null
}

function onMove(e: PointerEvent) {
  const rect = canvasRef.value!.getBoundingClientRect()
  const px = e.clientX - rect.left
  const py = e.clientY - rect.top
  if (dragId) {
    const n = byId(dragId)
    if (n) { n.x = px + dragDX; n.y = py + dragDY }
    return
  }
  const hit = pickAt(px, py)
  hoverId = hit?.id ?? null
  if (canvasRef.value) canvasRef.value.style.cursor = hit ? 'pointer' : 'default'
}

function onDown(e: PointerEvent) {
  const rect = canvasRef.value!.getBoundingClientRect()
  const px = e.clientX - rect.left
  const py = e.clientY - rect.top
  const hit = pickAt(px, py)
  if (hit) {
    dragId = hit.id
    dragDX = hit.x - px
    dragDY = hit.y - py
    canvasRef.value?.setPointerCapture(e.pointerId)
  }
}

function onUp(e: PointerEvent) {
  const rect = canvasRef.value!.getBoundingClientRect()
  const px = e.clientX - rect.left
  const py = e.clientY - rect.top
  const hit = pickAt(px, py)
  // 判定为点击（未明显拖动）
  if (hit && dragId === hit.id) {
    const moved = Math.hypot(px + dragDX - hit.x, py + dragDY - hit.y)
    if (moved < 6) emit('select', hit)
  }
  dragId = null
  try { canvasRef.value?.releasePointerCapture(e.pointerId) } catch { /* */ }
}

function rebuild() {
  resize()
  initPhysics()
}

let ro: ResizeObserver | null = null

onMounted(() => {
  rebuild()
  raf = requestAnimationFrame(loop)
  ro = new ResizeObserver(() => resize())
  if (wrapRef.value) ro.observe(wrapRef.value)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  ro?.disconnect()
})

// 数据变化时重建
watch(graphData, () => rebuild())
</script>

<template>
  <div ref="wrapRef" class="memory-graph">
    <canvas
      ref="canvasRef"
      @pointermove="onMove"
      @pointerdown="onDown"
      @pointerup="onUp"
      @pointerleave="hoverId = null"
    />
    <div class="graph-hint">拖拽节点可整理布局 · 点击节点查看细节</div>
  </div>
</template>

<style scoped>
.memory-graph {
  position: relative;
  width: 100%;
  height: 380px;
  border-radius: var(--radius-md);
  background:
    radial-gradient(circle at 30% 30%, rgba(99, 91, 255, 0.06), transparent 60%),
    var(--surface);
  overflow: hidden;
  touch-action: none;
}

.graph-hint {
  position: absolute;
  left: 12px;
  bottom: 10px;
  color: var(--ink-muted);
  font-size: 0.72rem;
  pointer-events: none;
  opacity: 0.7;
}
</style>
