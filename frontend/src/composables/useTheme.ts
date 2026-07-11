/**
 * 商家端浅色/深色主题切换。
 *
 * - 主题写入 <html data-theme="light|dark">，CSS 通过 [data-theme=dark] 覆盖变量
 * - localStorage 持久化用户选择
 * - 首次访问跟随系统 prefers-color-scheme
 *
 * 说明：管理端使用独立的浅色 Command Center 主题（body:has(.admin-route)），
 * 不受此切换影响。
 */
import { ref } from 'vue'

export type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'keliu:theme'
const theme = ref<ThemeMode>('light')
let initialized = false

function apply(mode: ThemeMode) {
  document.documentElement.setAttribute('data-theme', mode)
}

function detectInitial(): ThemeMode {
  const saved = localStorage.getItem(STORAGE_KEY) as ThemeMode | null
  if (saved === 'light' || saved === 'dark') return saved
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  return prefersDark ? 'dark' : 'light'
}

export function useTheme() {
  if (!initialized) {
    initialized = true
    theme.value = detectInitial()
    apply(theme.value)
  }

  function setTheme(mode: ThemeMode) {
    theme.value = mode
    localStorage.setItem(STORAGE_KEY, mode)
    apply(mode)
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  return { theme, setTheme, toggleTheme }
}
