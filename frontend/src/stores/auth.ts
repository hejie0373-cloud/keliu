import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { User } from '@/types/auth'
import * as authApi from '@/api/auth'

type OtpPurpose = 'login' | 'register' | 'reset_password' | 'bind_identity' | 'change_phone'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('accessToken'))
  const refreshToken = ref<string | null>(null)

  const isLoggedIn = computed(() => !!accessToken.value)
  const hasStore = computed(() => !!user.value?.storeId)
  const roles = computed(() => user.value?.roles || [])

  async function sendCode(account: string, purpose: OtpPurpose = 'login') {
    await authApi.sendCode(account, purpose)
  }

  async function loginByPhone(account: string, code: string) {
    const { data } = await authApi.loginByPhone(account, code)
    setTokens(data.accessToken)
    await fetchMe()
  }

  async function loginByPassword(account: string, password: string) {
    const { data } = await authApi.loginByPassword(account, password)
    setTokens(data.accessToken)
    await fetchMe()
  }

  async function loginByEmail(email: string, password: string) {
    await loginByPassword(email, password)
  }

  async function registerByPhone(account: string, code: string, password: string) {
    const { data } = await authApi.registerByPhone(account, code, password)
    setTokens(data.accessToken)
    await fetchMe()
  }

  async function registerByEmail(email: string, password: string) {
    const { data } = await authApi.registerByPassword(email, password)
    setTokens(data.accessToken)
    await fetchMe()
    return data
  }

  async function fetchMe() {
    try {
      const { data } = await authApi.getMe({ silentError: true })
      user.value = data
    } catch {
      // unauthenticated or expired token
    }
  }

  function setTokens(access: string, _refresh?: string | null) {
    accessToken.value = access
    localStorage.setItem('accessToken', access)
  }

  async function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('accessToken')
    try { await authApi.logout() } catch { /* ignore */ }
  }

  return {
    user, accessToken, refreshToken, isLoggedIn, hasStore, roles,
    sendCode, registerByPhone, registerByEmail, loginByPhone, loginByPassword, loginByEmail,
    fetchMe, setTokens, logout,
  }
})
