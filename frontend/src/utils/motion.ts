/**
 * GSAP 动效引擎
 *
 * 统一封装项目里用到的动效，并内置 prefers-reduced-motion 守卫：
 * 当用户系统开启了「减少动态效果」时，所有动画降级为「瞬间到达终态」，
 * 不做任何位移/透明度过渡，保证可访问性。
 */
import { gsap } from 'gsap'

/** 用户是否要求减少动态效果 */
export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Stripe 风格的标准缓动 */
export const EASE = {
  out: 'power3.out',
  inOut: 'power2.inOut',
  spring: 'back.out(1.6)',
} as const

/**
 * 卡片/区块 stagger 进场：从下方 12px + 透明淡入，错落进入。
 * reduced-motion 下直接清空内联样式（终态）。
 */
export function revealStagger(
  targets: gsap.TweenTarget,
  opts: { delay?: number; stagger?: number; y?: number } = {},
) {
  const { delay = 0, stagger = 0.06, y = 12 } = opts
  if (prefersReducedMotion()) {
    gsap.set(targets, { clearProps: 'all' })
    return
  }
  return gsap.fromTo(
    targets,
    { opacity: 0, y },
    { opacity: 1, y: 0, duration: 0.5, ease: EASE.out, stagger, delay },
  )
}

/**
 * 数字滚动：把一个对象的 val 从 from 补间到 to，每帧回调更新。
 * reduced-motion 下直接回调终值。
 */
export function tweenNumber(
  from: number,
  to: number,
  onUpdate: (v: number) => void,
  opts: { duration?: number; delay?: number } = {},
) {
  const { duration = 1.1, delay = 0 } = opts
  if (prefersReducedMotion()) {
    onUpdate(to)
    return
  }
  const obj = { val: from }
  return gsap.to(obj, {
    val: to,
    duration,
    delay,
    ease: EASE.out,
    onUpdate: () => onUpdate(obj.val),
  })
}

/**
 * 进度条 / 宽度类填充动画：0 → targetPct(%)。
 */
export function tweenWidth(
  el: Element,
  targetPct: number,
  opts: { duration?: number; delay?: number } = {},
) {
  const { duration = 0.9, delay = 0.1 } = opts
  if (prefersReducedMotion()) {
    gsap.set(el, { width: `${targetPct}%` })
    return
  }
  return gsap.fromTo(
    el,
    { width: '0%' },
    { width: `${targetPct}%`, duration, delay, ease: EASE.out },
  )
}

/** 元素微浮起（hover 进入） */
export function liftIn(el: Element) {
  if (prefersReducedMotion()) return
  gsap.to(el, { y: -4, duration: 0.25, ease: EASE.out })
}

/** 元素落回（hover 离开） */
export function liftOut(el: Element) {
  if (prefersReducedMotion()) return
  gsap.to(el, { y: 0, duration: 0.25, ease: EASE.out })
}
