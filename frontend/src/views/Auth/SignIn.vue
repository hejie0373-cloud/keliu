<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import QRCode from 'qrcode'
import AuthModeTabs from '@/components/auth/AuthModeTabs.vue'
import AuthShell from '@/components/auth/AuthShell.vue'
import AuthTextInput from '@/components/auth/AuthTextInput.vue'
import { pulsePanel, revealAuthSurface } from '@/components/auth/authMotion'
import { bindWechatByPassword, exchangeLoginTicket, getWechatQrUrl, getWechatStatus } from '@/api/auth'
import { getApiErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const pageRoot = ref<HTMLElement | null>(null)
const formPanel = ref<HTMLElement | null>(null)
const bindPanel = ref<HTMLElement | null>(null)

const mode = ref<'email' | 'code' | 'wechat'>('email')
const loading = ref(false)
const countdown = ref(0)
const email = ref('')
const emailPassword = ref('')
const phoneAccount = ref('')
const code = ref('')
const bindAccount = ref('')
const bindPassword = ref('')
const agreedToTerms = ref(false)
const showEmailPassword = ref(false)
const showBindPassword = ref(false)

const qrSrc = ref('')
const qrTip = ref('使用微信扫描二维码')
const qrExpired = ref(false)
const wechatBinding = ref(false)
const bindLoading = ref(false)
const pendingWechatLoginTicket = ref('')
let qrState = ''
let countdownTimer: number | null = null
let pollTimer: number | null = null
let expireTimer: number | null = null
let refreshTimer: number | null = null
let cleanupReveal: (() => void) | null = null

const loginModes = computed(() => [
  { label: '邮箱登录', value: 'email' },
  { label: '手机登录', value: 'code' },
  { label: '微信扫码', value: 'wechat' },
])

function validEmail(value = email.value) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim().toLowerCase())
}

function validPhone(value = phoneAccount.value) {
  return /^1[3-9]\d{9}$/.test(value.trim())
}

function validBindAccount() {
  const value = bindAccount.value.trim()
  return /^1[3-9]\d{9}$/.test(value) || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value)
}

function ensureAgreement() {
  if (agreedToTerms.value) return true
  ElMessage.warning('请先阅读并勾选用户协议和隐私政策')
  return false
}

function errorDetail(error: unknown) {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
}

function startCodeCountdown(seconds = 60) {
  countdown.value = seconds
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0 && countdownTimer) clearInterval(countdownTimer)
  }, 1000)
}

async function genQR() {
  qrExpired.value = false
  pendingWechatLoginTicket.value = ''
  qrTip.value = '二维码加载中'
  if (refreshTimer) clearInterval(refreshTimer)
  if (expireTimer) clearTimeout(expireTimer)

  try {
    const { data } = await getWechatQrUrl()
    qrState = data.state
    qrSrc.value = await QRCode.toDataURL(data.qrUrl, { width: 180, margin: 1 })
    qrTip.value = '使用微信扫描二维码'
    startPolling()

    refreshTimer = window.setInterval(async () => {
      if (!pendingWechatLoginTicket.value && !qrExpired.value && mode.value === 'wechat') await genQR()
    }, 120 * 1000)

    expireTimer = window.setTimeout(() => {
      qrExpired.value = true
      qrTip.value = '二维码已过期'
      stopPolling()
      if (refreshTimer) clearInterval(refreshTimer)
    }, Math.max(30, data.expiresIn - 5) * 1000)
  } catch {
    qrTip.value = '二维码加载失败'
    qrExpired.value = true
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    if (!qrState || qrExpired.value || mode.value !== 'wechat') return
    try {
      const { data } = await getWechatStatus(qrState)
      if (data.status === 'confirmed' && data.loginTicket) {
        stopPolling()
        if (expireTimer) clearTimeout(expireTimer)
        await completeWechatLogin(data.loginTicket)
      } else if (data.status === 'expired') {
        qrExpired.value = true
        qrTip.value = '二维码已过期'
        stopPolling()
      } else if (data.status === 'unbound') {
        wechatBinding.value = true
        qrTip.value = '首次微信登录，请绑定已有账号'
        stopPolling()
      } else {
        qrTip.value = '请在微信中确认授权'
      }
    } catch {
      // Keep polling; transient network errors should not hide the QR code.
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function refreshQR() {
  wechatBinding.value = false
  pendingWechatLoginTicket.value = ''
  void genQR()
}

async function completeWechatLogin(loginTicket: string) {
  if (!agreedToTerms.value) {
    pendingWechatLoginTicket.value = loginTicket
    qrTip.value = '请先勾选协议后继续登录'
    ensureAgreement()
    return
  }

  pendingWechatLoginTicket.value = ''
  qrTip.value = '登录成功'
  const ticketResult = await exchangeLoginTicket(loginTicket)
  auth.setTokens(ticketResult.data.accessToken)
  await auth.fetchMe()
  onLoginSuccess()
}

async function handleEmailLogin() {
  if (!validEmail()) {
    ElMessage.warning('请输入正确的邮箱地址')
    return
  }
  if (!emailPassword.value) {
    ElMessage.warning('请输入邮箱账号密码')
    return
  }

  loading.value = true
  try {
    await auth.loginByEmail(email.value.trim().toLowerCase(), emailPassword.value)
    ElMessage.success('邮箱登录成功')
    onLoginSuccess()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '邮箱登录失败'))
  } finally {
    loading.value = false
  }
}

async function handleSendCode() {
  if (!validPhone()) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (countdown.value > 0) return
  loading.value = true
  try {
    await auth.sendCode(phoneAccount.value.trim(), 'login')
    ElMessage.success('验证码已发送')
    startCodeCountdown()
  } catch (error) {
    if (errorDetail(error) === 'OTP_RATE_LIMITED') {
      ElMessage.warning('验证码发送太频繁，请稍后再试')
      startCodeCountdown()
    } else {
      ElMessage.error('验证码发送失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

async function handlePhoneLogin() {
  if (!validPhone()) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (!/^\d{6}$/.test(code.value)) {
    ElMessage.warning('请输入 6 位验证码')
    return
  }

  loading.value = true
  try {
    await auth.loginByPhone(phoneAccount.value.trim(), code.value)
    onLoginSuccess()
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!ensureAgreement()) return
  if (mode.value === 'email') {
    await handleEmailLogin()
  } else if (mode.value === 'code') {
    await handlePhoneLogin()
  }
}

async function handleWechatBind() {
  if (!qrState) return
  if (!ensureAgreement()) return
  if (!validBindAccount()) {
    ElMessage.warning('请输入正确的手机号或邮箱')
    return
  }
  if (!bindPassword.value) {
    ElMessage.warning('请输入该账号的登录密码')
    return
  }
  bindLoading.value = true
  try {
    const { data } = await bindWechatByPassword(qrState, bindAccount.value.trim(), bindPassword.value)
    if (data.status === 'confirmed' && data.loginTicket) {
      const ticketResult = await exchangeLoginTicket(data.loginTicket)
      auth.setTokens(ticketResult.data.accessToken)
      await auth.fetchMe()
      ElMessage.success('微信已绑定，登录成功')
      onLoginSuccess()
    }
  } finally {
    bindLoading.value = false
  }
}

function onLoginSuccess() {
  const redirect = router.currentRoute.value.query.redirect as string
  if (redirect) {
    router.push(redirect)
  } else if (auth.roles.includes('super_admin')) {
    router.push('/admin')
  } else if (auth.hasStore) {
    router.push('/dashboard')
  } else {
    router.push('/onboarding')
  }
}

watch(mode, (nextMode) => {
  void nextTick(() => pulsePanel(formPanel.value))
  if (nextMode === 'wechat') {
    void genQR()
  } else {
    pendingWechatLoginTicket.value = ''
    stopPolling()
  }
})

watch(wechatBinding, (active) => {
  if (active) void nextTick(() => pulsePanel(bindPanel.value))
})

watch(agreedToTerms, (accepted) => {
  if (accepted && mode.value === 'wechat' && pendingWechatLoginTicket.value) {
    void completeWechatLogin(pendingWechatLoginTicket.value)
  }
})

onMounted(() => {
  cleanupReveal = revealAuthSurface(pageRoot.value)
})

onUnmounted(() => {
  cleanupReveal?.()
  if (countdownTimer) clearInterval(countdownTimer)
  if (expireTimer) clearTimeout(expireTimer)
  if (refreshTimer) clearInterval(refreshTimer)
  stopPolling()
})
</script>

<template>
  <div ref="pageRoot">
    <AuthShell>
      <div class="auth-header" data-auth-item>
        <div class="brand-title">
          <span class="brand-emblem" aria-hidden="true">
            <img src="@/assets/keliu.png" alt="" />
          </span>
          <div class="brand-copy">
            <h1>客留</h1>
            <p>商家经营工作台</p>
          </div>
        </div>
      </div>

      <AuthModeTabs v-model="mode" :options="loginModes" data-auth-item />

      <div ref="formPanel" class="form-area" data-auth-item>
        <div v-if="mode === 'email'">
          <AuthTextInput
            v-model="email"
            label="邮箱"
            placeholder="name@qq.com"
            autocomplete="email"
            inputmode="email"
            @enter="handleSubmit"
          >
            <template #prefix>邮箱</template>
          </AuthTextInput>

          <AuthTextInput
            v-model="emailPassword"
            label="密码"
            :type="showEmailPassword ? 'text' : 'password'"
            placeholder="邮箱密码"
            autocomplete="current-password"
            @enter="handleSubmit"
          >
            <template #prefix>密码</template>
            <template #action>
              <button class="inline-action" type="button" @click="showEmailPassword = !showEmailPassword">
                {{ showEmailPassword ? '隐藏' : '显示' }}
              </button>
            </template>
          </AuthTextInput>
        </div>

        <div v-else-if="mode === 'code'">
          <AuthTextInput
            v-model="phoneAccount"
            label="手机号"
            placeholder="请输入手机号"
            autocomplete="tel"
            inputmode="tel"
            @enter="handleSubmit"
          >
            <template #prefix>手机</template>
          </AuthTextInput>

          <AuthTextInput
            v-model="code"
            label="验证码"
            placeholder="请输入 6 位验证码"
            :maxlength="6"
            inputmode="numeric"
            autocomplete="one-time-code"
            @enter="handleSubmit"
          >
            <template #prefix>验证码</template>
            <template #action>
              <button class="inline-action" type="button" :disabled="countdown > 0" @click="handleSendCode">
                {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
              </button>
            </template>
          </AuthTextInput>
        </div>

        <div v-else class="wechat-area">
          <div class="qr-box" :class="{ expired: qrExpired }">
            <img v-if="qrSrc && !qrExpired && !wechatBinding" :src="qrSrc" alt="微信登录二维码">
            <button v-if="qrExpired && !wechatBinding" class="qr-overlay" type="button" @click="refreshQR">刷新二维码</button>
            <div v-if="wechatBinding" class="qr-placeholder">待绑定</div>
            <div v-else-if="!qrSrc && !qrExpired" class="qr-placeholder">加载中</div>
          </div>
          <div class="wechat-title">
            <div class="wechat-brand" aria-hidden="true">
              <svg viewBox="0 0 32 32" focusable="false">
                <path d="M13.6 8.4c-5.3 0-9.6 3.4-9.6 7.6 0 2.3 1.3 4.3 3.4 5.7l-.8 2.8 3.2-1.6c1.1.4 2.4.7 3.8.7 5.3 0 9.6-3.4 9.6-7.6s-4.3-7.6-9.6-7.6Z" />
                <path d="M19.2 15.2c4.8.2 8.6 3.2 8.6 7 0 2-1.1 3.8-2.9 5.1l.7 2.3-2.8-1.4c-1 .4-2.2.6-3.5.6-4.9 0-8.9-3.1-8.9-6.9 0-3.7 3.8-6.7 8.8-6.7Z" />
                <circle cx="10.8" cy="14.7" r="1.1" />
                <circle cx="16.4" cy="14.7" r="1.1" />
                <circle cx="17.1" cy="21.4" r=".9" />
                <circle cx="22.2" cy="21.4" r=".9" />
              </svg>
            </div>
            <strong>微信扫码登录</strong>
          </div>
          <span>{{ qrTip }}</span>
        </div>

        <button
          v-if="mode !== 'wechat'"
          class="primary-btn"
          type="button"
          :disabled="loading"
          @click="handleSubmit"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </div>

      <div v-if="wechatBinding" ref="bindPanel" class="bind-panel">
        <div class="bind-title">
          <strong>绑定已有账号</strong>
          <span>首次微信登录需要确认账号归属。</span>
        </div>

        <AuthTextInput
          v-model="bindAccount"
          label="绑定账号"
          placeholder="请输入已注册手机号或邮箱"
          autocomplete="username"
          inputmode="email"
        >
          <template #prefix>账号</template>
        </AuthTextInput>

        <AuthTextInput
          v-model="bindPassword"
          label="登录密码"
          :type="showBindPassword ? 'text' : 'password'"
          placeholder="输入该账号密码"
          autocomplete="current-password"
          @enter="handleWechatBind"
        >
          <template #prefix>密码</template>
          <template #action>
            <button class="inline-action" type="button" @click="showBindPassword = !showBindPassword">
              {{ showBindPassword ? '隐藏' : '显示' }}
            </button>
          </template>
        </AuthTextInput>

        <button class="primary-btn" type="button" :disabled="bindLoading" @click="handleWechatBind">
          {{ bindLoading ? '绑定中...' : '绑定并登录' }}
        </button>
      </div>

      <div class="helper-row" data-auth-item>
        <button type="button" @click="mode = 'code'">手机验证码登录</button>
        <button type="button" @click="router.push('/auth/signup')">免费注册</button>
      </div>

      <label class="agree-check" data-auth-item>
        <input v-model="agreedToTerms" type="checkbox">
        <span>
          我已阅读并同意
          <a href="#" @click.stop>用户协议</a>
          和
          <a href="#" @click.stop>隐私政策</a>
        </span>
      </label>
    </AuthShell>
  </div>
</template>

<style scoped>
.auth-header {
  display: flex;
  justify-content: center;
}

.brand-title {
  display: inline-grid;
  grid-template-columns: auto auto;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 2px 8px 4px;
}

.brand-emblem {
  width: 86px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
  border: 1px solid rgba(217, 173, 85, 0.22);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.92), rgba(243, 231, 204, 0.48));
  box-shadow: 0 14px 30px rgba(97, 72, 26, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.82);
  filter: drop-shadow(0 10px 18px rgba(97, 72, 26, 0.16));
}

.brand-emblem img {
  width: 78px;
  height: 34px;
  object-fit: contain;
  display: block;
}

.brand-copy {
  display: grid;
  gap: 3px;
}

.brand-copy h1 {
  margin: 0;
  color: #101827;
  font-size: 2rem;
  line-height: 1;
  letter-spacing: 0;
}

.brand-copy p {
  margin: 0;
  color: #5f6f80;
  font-size: 0.88rem;
  font-weight: 680;
  line-height: 1.2;
}

.form-area {
  position: relative;
}

.inline-action {
  height: 100%;
  min-width: 92px;
  padding: 0 12px;
  border: 0;
  background: linear-gradient(180deg, rgba(250, 253, 254, 0.9), rgba(238, 246, 249, 0.82));
  color: #0f6f88;
  font: inherit;
  font-size: 0.84rem;
  font-weight: 760;
  white-space: nowrap;
  cursor: pointer;
  transition: background 180ms ease, color 180ms ease;
}

.inline-action:hover {
  background: #ffffff;
  color: #0b596d;
}

.inline-action:disabled {
  color: #97a3b2;
  cursor: not-allowed;
}

.primary-btn {
  width: 100%;
  min-height: 50px;
  position: relative;
  overflow: hidden;
  border: 0;
  border-radius: 8px;
  background: linear-gradient(135deg, #0d7188 0%, #1091a3 52%, #0b687d 100%);
  color: #fff;
  font: inherit;
  font-size: 0.96rem;
  font-weight: 780;
  cursor: pointer;
  box-shadow: 0 16px 32px rgba(15, 111, 136, 0.26), inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition: box-shadow 180ms ease, filter 180ms ease;
}

.primary-btn::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 -40%;
  width: 36%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.32), transparent);
  transform: skewX(-18deg);
  transition: transform 520ms ease;
}

.primary-btn:hover {
  filter: saturate(1.08);
  box-shadow: 0 20px 40px rgba(15, 111, 136, 0.31), inset 0 1px 0 rgba(255, 255, 255, 0.24);
}

.primary-btn:hover::before {
  transform: translateX(410%) skewX(-18deg);
}

.primary-btn:disabled {
  opacity: 0.62;
  cursor: not-allowed;
  transform: none;
}

.wechat-area {
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 10px 0 4px;
  color: #667386;
  text-align: center;
}

.wechat-title {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.wechat-brand {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: linear-gradient(135deg, #12a94b, #18c465);
  box-shadow: 0 10px 20px rgba(22, 163, 74, 0.24);
  flex: 0 0 auto;
}

.wechat-brand svg {
  width: 18px;
  height: 18px;
  fill: #fff;
}

.wechat-title strong {
  color: #172033;
  font-size: 1rem;
}

.wechat-area span {
  font-size: 0.86rem;
}

.qr-box {
  width: 184px;
  height: 184px;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(22, 163, 74, 0.2);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fcf9 100%);
  box-shadow: inset 0 0 0 8px rgba(22, 163, 74, 0.05), 0 18px 36px rgba(15, 23, 42, 0.09);
}

.qr-box::after {
  content: '';
  position: absolute;
  left: 16px;
  right: 16px;
  top: 24px;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(22, 163, 74, 0.55), transparent);
  box-shadow: 0 0 14px rgba(22, 163, 74, 0.36);
  animation: qrScan 2.4s ease-in-out infinite;
}

.qr-box img {
  width: 164px;
  height: 164px;
  border-radius: 6px;
}

.qr-overlay {
  position: absolute;
  inset: 0;
  border: 0;
  background: rgba(255, 255, 255, 0.94);
  color: #0f6f88;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 760;
  cursor: pointer;
}

.qr-placeholder {
  color: #667386;
  font-size: 0.88rem;
}

.bind-panel {
  margin-top: 18px;
  padding: 16px;
  border: 1px solid rgba(15, 111, 136, 0.16);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(242, 251, 252, 0.92), rgba(235, 246, 249, 0.82));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.bind-title {
  margin-bottom: 14px;
}

.bind-title strong,
.bind-title span {
  display: block;
}

.bind-title strong {
  color: #172033;
  font-size: 0.96rem;
}

.bind-title span {
  margin-top: 4px;
  color: #667386;
  font-size: 0.84rem;
}

.helper-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 18px;
}

.helper-row button {
  padding: 0;
  border: 0;
  background: transparent;
  color: #0f6f88;
  font: inherit;
  font-size: 0.88rem;
  font-weight: 760;
  cursor: pointer;
  transition: color 160ms ease, transform 160ms ease;
}

.helper-row button:hover {
  color: #0b596d;
  transform: translateY(-1px);
}

.agree-check {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin: 16px 0 0;
  color: #7a8797;
  font-size: 0.76rem;
  line-height: 1.7;
  cursor: pointer;
}

.agree-check input {
  width: 15px;
  height: 15px;
  margin: 3px 0 0;
  flex: 0 0 auto;
  accent-color: #0f6f88;
}

.agree-check a {
  color: #0f6f88;
  font-weight: 680;
}

@keyframes qrScan {
  0%,
  100% {
    transform: translateY(0);
    opacity: 0.22;
  }

  50% {
    transform: translateY(132px);
    opacity: 0.78;
  }
}

button:focus-visible,
a:focus-visible {
  outline: 3px solid rgba(15, 111, 136, 0.22);
  outline-offset: 2px;
}

@media (max-width: 420px) {
  .helper-row {
    flex-direction: column;
    align-items: center;
  }
}
</style>
