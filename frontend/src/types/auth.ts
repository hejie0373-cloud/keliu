export interface User {
  id: string
  name: string | null
  phone: string | null
  email: string | null
  avatarUrl: string | null
  isActive: boolean
  roles: string[]
  storeId: string | null
  createdAt: string
}

export interface TokenResponse {
  accessToken: string
  refreshToken?: string | null
  tokenType: string
  expiresIn: number
}

export interface LoginByOtpForm {
  account: string
  code: string
}

export interface LoginByPasswordForm {
  account: string
  password: string
}
