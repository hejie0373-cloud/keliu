import http from './http'
import type { TokenResponse, User } from '@/types/auth'

export const sendCode = (account: string, purpose: 'login' | 'register' | 'reset_password' | 'bind_identity' | 'change_phone' = 'login') =>
  http.post<{ message: string }>('/auth/send-code', { account, purpose }, { silentError: true })

export const loginByPhone = (account: string, code: string) =>
  http.post<TokenResponse>('/auth/login/phone', { account, code })

export const loginByPassword = (account: string, password: string) =>
  http.post<TokenResponse>('/auth/login/password', { account, password })

export const registerByPhone = (account: string, code: string, password: string) =>
  http.post<TokenResponse>('/auth/register/phone', { account, code, password })

export const registerByPassword = (account: string, password: string) =>
  http.post<TokenResponse>('/auth/register/password', { account, password })

export const refreshToken = () =>
  http.post<TokenResponse>('/auth/refresh')

export const logout = () =>
  http.post<{ message: string }>('/auth/logout')

export const exchangeLoginTicket = (loginTicket: string) =>
  http.post<TokenResponse>('/auth/login-ticket/exchange', { loginTicket })

export const getMe = (options?: { silentError?: boolean }) =>
  http.get<User>('/users/me', options)

export const updateProfile = (data: { name?: string; avatarUrl?: string }) =>
  http.put<{ message: string }>('/users/me', data)

export const changePassword = (oldPassword: string, newPassword: string) =>
  http.post<{ message: string }>('/users/me/change-password', { oldPassword, newPassword })

export const changePhone = (phone: string, code: string) =>
  http.post<{ message: string }>('/users/me/change-phone', { phone, code })

// ---- QR 扫码登录 ----

export const qrGenerate = () =>
  http.post<{ qrId: string; qrUrl: string; qrImage: string; expiresIn: number }>('/auth/qr/generate')

export const qrStatus = (qrId: string) =>
  http.get<{ status: string; loginTicket?: string; userName?: string }>(`/auth/qr/status/${qrId}`)

export const qrConfirm = (qrId: string) =>
  http.post<{ message: string }>('/auth/qr/confirm', { qrId })

// ---- 微信扫码登录 ----

export const getWechatQrUrl = () =>
  http.get<{ qrUrl: string; state: string; expiresIn: number }>('/auth/wechat/qr-url')

export const getWechatStatus = (state: string) =>
  http.get<{ status: string; loginTicket?: string; message?: string }>(`/auth/wechat/status/${state}`)

export const bindWechatByPassword = (state: string, account: string, password: string) =>
  http.post<{ status: string; loginTicket?: string; message?: string }>('/auth/wechat/bind-password', {
    state,
    account,
    password,
  })
