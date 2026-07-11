/**
 * v-reveal 指令：元素进入视口时触发子元素 stagger 渐入。
 *
 * 用法：
 *   <section v-reveal>            // 直接子元素依次渐入
 *   <section v-reveal="'.card'">  // 指定选择器的后代依次渐入
 *
 * 基于 IntersectionObserver，只触发一次；reduced-motion 下由 motion.ts 降级。
 */
import type { Directive } from 'vue'
import { revealStagger } from '@/utils/motion'

interface RevealEl extends HTMLElement {
  _revealObserver?: IntersectionObserver
}

export const vReveal: Directive<RevealEl, string | undefined> = {
  mounted(el, binding) {
    const selector = binding.value
    const targets = selector
      ? Array.from(el.querySelectorAll<HTMLElement>(selector))
      : Array.from(el.children) as HTMLElement[]

    if (!targets.length) return

    // 初始隐藏，避免进场前闪现
    targets.forEach((t) => {
      t.style.opacity = '0'
    })

    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            revealStagger(targets)
            obs.disconnect()
          }
        })
      },
      { threshold: 0.08 },
    )
    observer.observe(el)
    el._revealObserver = observer
  },
  unmounted(el) {
    el._revealObserver?.disconnect()
  },
}
