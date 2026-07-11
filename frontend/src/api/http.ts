import axios from 'axios'
import camelcaseKeys from 'camelcase-keys'
import snakecaseKeys from 'snakecase-keys'
import { ElMessage } from 'element-plus'

declare module 'axios' {
  interface AxiosRequestConfig {
    silentError?: boolean
    _retry?: boolean
  }
}

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

const ERROR_MESSAGES: Record<string, string> = {
  ACCOUNT_ALREADY_REGISTERED: '账号已注册',
  ACCOUNT_FORMAT_INVALID: '请输入正确的手机号或邮箱',
  ACCOUNT_NOT_REGISTERED: '账号未注册',
  ACCOUNT_OR_PASSWORD_INVALID: '账号或密码错误',
  FEATURE_REQUIRES_UPGRADE: '当前套餐不包含此功能，请升级套餐后继续使用',
  IDENTITY_ALREADY_BOUND: '该账号已被绑定',
  INTERNAL_ERROR: '服务器内部错误，请稍后再试',
  LOGIN_TICKET_INVALID: '登录凭证无效，请重新登录',
  OTP_INVALID_OR_EXPIRED: '验证码错误或已过期',
  OTP_PURPOSE_INVALID: '验证码用途无效',
  OTP_RATE_LIMITED: '验证码发送太频繁，请稍后再试',
  OTP_SEND_FAILED: '验证码发送失败，请稍后重试',
  REFRESH_TOKEN_REQUIRED: '登录已过期，请重新登录',
  TOKEN_INVALID: '登录已过期，请重新登录',
  TOKEN_REUSE_DETECTED: '登录状态异常，请重新登录',
  TOKEN_REVOKED: '登录已过期，请重新登录',
  TOKEN_TYPE_INVALID: '登录已过期，请重新登录',
  TRIAL_CREDITS_EXHAUSTED: '免费体验次数已用完，请开通套餐后继续使用',
  USER_DISABLED: '账号已被禁用',
  USER_NOT_FOUND_OR_DISABLED: '账号不存在或已被禁用',
}

const STATUS_MESSAGES: Record<number, string> = {
  400: '请求参数有误',
  401: '登录已过期，请重新登录',
  403: '没有权限执行此操作',
  404: '请求的资源不存在',
  409: '数据冲突，请刷新后重试',
  422: '提交内容格式不正确',
  429: '操作太频繁，请稍后再试',
  500: '服务器内部错误，请稍后再试',
  502: '网关服务异常，请稍后再试',
  503: '服务暂时不可用，请稍后再试',
}

function isEnglishAxiosMessage(message?: string) {
  return Boolean(message && /^Request failed with status code \d+$/i.test(message))
}

function hasChinese(message?: string) {
  return Boolean(message && /[\u4e00-\u9fff]/.test(message))
}

export function getApiErrorMessage(error: unknown, fallback = '请求失败，请稍后重试') {
  const err = error as {
    message?: string
    response?: {
      status?: number
      data?: {
        detail?: string
        message?: string
      }
    }
  }
  const detail = err.response?.data?.detail || err.response?.data?.message
  if (detail && ERROR_MESSAGES[detail]) return ERROR_MESSAGES[detail]
  if (detail && hasChinese(detail)) return detail
  if (err.response?.status && STATUS_MESSAGES[err.response.status]) return STATUS_MESSAGES[err.response.status]
  if (err.message === 'Network Error') return '网络连接失败，请检查后重试'
  if (err.message?.toLowerCase().includes('timeout')) return '请求超时，请稍后重试'
  if (err.message && !isEnglishAxiosMessage(err.message) && hasChinese(err.message)) return err.message
  return fallback
}

function localizeError(error: unknown) {
  const err = error as { message?: string }
  err.message = getApiErrorMessage(error)
  return err
}

function shouldRefreshToken(config: { url?: string; _retry?: boolean } | undefined, status?: number) {
  if (status !== 401 || !config || config._retry) return false
  const url = config.url || ''
  return !url.startsWith('/auth/')
}

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.data && typeof config.data === 'object' && !(config.data instanceof FormData)) {
    config.data = snakecaseKeys(config.data, { deep: true })
  }
  if (config.params && typeof config.params === 'object') {
    config.params = snakecaseKeys(config.params, { deep: true })
  }
  return config
})

let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

http.interceptors.response.use(
  (response) => {
    if (
      response.data &&
      typeof response.data === 'object' &&
      !(response.data instanceof Blob) &&
      response.config?.responseType !== 'blob'
    ) {
      response.data = camelcaseKeys(response.data, { deep: true })
    }
    return response
  },
  async (error) => {
    const { config, response } = error
    const silentError = config?.silentError === true

    if (shouldRefreshToken(config, response?.status)) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshSubscribers.push((token: string) => {
            config.headers.Authorization = `Bearer ${token}`
            resolve(http(config))
          })
        })
      }

      config._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post('/api/auth/refresh', undefined, { withCredentials: true })
        const newAccess = data.access_token || data.accessToken

        localStorage.setItem('accessToken', newAccess)
        onRefreshed(newAccess)
        isRefreshing = false

        config.headers.Authorization = `Bearer ${newAccess}`
        return http(config)
      } catch {
        isRefreshing = false
        redirectToLogin()
        return Promise.reject(localizeError(error))
      }
    }

    const message = getApiErrorMessage(error)
    if (silentError) {
      return Promise.reject(localizeError(error))
    }

    if (response?.status === 402) {
      ElMessage.warning(message)
      if (!window.location.pathname.startsWith('/billing')) {
        window.location.href = '/billing'
      }
      return Promise.reject(localizeError(error))
    }

    if (response?.status !== 401) {
      ElMessage.error(message)
    }
    return Promise.reject(localizeError(error))
  },
)

function redirectToLogin() {
  localStorage.removeItem('accessToken')
  if (!window.location.pathname.startsWith('/auth/')) {
    window.location.href = '/auth/signin'
  }
}

export default http
