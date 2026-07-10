<script setup lang="ts">
/**
 * 数字滚动组件：进入视口后从 0（或指定起点）补间到目标值，带千分位。
 * reduced-motion 下直接显示终值。
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { tweenNumber } from '@/utils/motion'

const props = withDefaults(defineProps<{
  value: number
  from?: number
  duration?: number
  delay?: number
  decimals?: number
  prefix?: string
  suffix?: string
  /** 是否千分位分隔 */
  group?: boolean
}>(), {
  from: 0,
  duration: 1.1,
  delay: 0,
  decimals: 0,
  prefix: '',
  suffix: '',
  group: true,
})

const display = ref('')
let tween: ReturnType<typeof tweenNumber> | undefined

function format(v: number): string {
  const fixed = v.toFixed(props.decimals)
  if (!props.group) return `${props.prefix}${fixed}${props.suffix}`
  const [int, dec] = fixed.split('.')
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return `${props.prefix}${dec ? `${grouped}.${dec}` : grouped}${props.suffix}`
}

function run(to: number) {
  tween?.kill?.()
  tween = tweenNumber(props.from, to, (v) => { display.value = format(v) }, {
    duration: props.duration,
    delay: props.delay,
  })
}

onMounted(() => {
  display.value = format(props.from)
  run(props.value)
})

watch(() => props.value, (v) => run(v))

onBeforeUnmount(() => tween?.kill?.())
</script>

<template>
  <span class="animated-number">{{ display }}</span>
</template>

<style scoped>
.animated-number {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
}
</style>
