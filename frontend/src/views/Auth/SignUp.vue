<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AuthModeTabs from '@/components/auth/AuthModeTabs.vue'
import AuthShell from '@/components/auth/AuthShell.vue'
import AuthTextInput from '@/components/auth/AuthTextInput.vue'
import { pulsePanel, revealAuthSurface } from '@/components/auth/authMotion'
import { getApiErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const pageRoot = ref<HTMLElement | null>(null)
const formPanel = ref<HTMLElement | null>(null)
const mode = ref<'email' | 'phone'>('email')
const email = ref((route.query.account as string) || '')
const phone = ref((route.query.phone as string) || '')
const code = ref((route.query.code as string) || '')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirm = ref(false)
const agreedToTerms = ref(false)
const loading = ref(false)
const countdown = ref(0)
let countdownTimer: number | null = null
let cleanupReveal: (() => void) | null = null

const registerModes = computed(() => [
  { label: '邮箱注册', value: 'email' },
  { label: '手机注册', value: 'phone' },
])

function validEmail() {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value.trim().toLowerCase())
}

function validPhone() {
  return /^1[3-9]\d{9}$/.test(phone.value.trim())
}

function validPassword() {
  if (!password.value || password.value.length < 8) {
    ElMessage.warning('密码至少 8 位')
    return false
  }
  if (password.value !== confirmPassword.value) {
    ElMessage.warning('两次输入的密码不一致')
    return false
  }
  return true
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

async function handleSendCode() {
  if (!validPhone()) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (countdown.value > 0) return

  loading.value = true
  try {
    await auth.sendCode(phone.value.trim(), 'register')
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

async function handleEmailRegister() {
  if (!validEmail()) {
    ElMessage.warning('请输入正确的邮箱地址')
    return
  }
  if (!validPassword()) return

  loading.value = true
  try {
    await auth.registerByEmail(email.value.trim().toLowerCase(), password.value)
    ElMessage.success('邮箱注册成功')
    onSuccess()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '邮箱注册失败'))
  } finally {
    loading.value = false
  }
}

async function handlePhoneRegister() {
  if (!validPhone()) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (!validPassword()) return
  if (!/^\d{6}$/.test(code.value)) {
    ElMessage.warning('请输入 6 位验证码')
    return
  }

  loading.value = true
  try {
    await auth.registerByPhone(phone.value.trim(), code.value, password.value)
    ElMessage.success('注册成功')
    onSuccess()
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!ensureAgreement()) return
  if (mode.value === 'email') {
    await handleEmailRegister()
  } else {
    await handlePhoneRegister()
  }
}

function onSuccess() {
  const redirect = router.currentRoute.value.query.from as string
  if (redirect) {
    router.push(redirect)
  } else if (auth.hasStore) {
    router.push('/dashboard')
  } else {
    router.push('/onboarding')
  }
}

watch(mode, () => {
  void nextTick(() => pulsePanel(formPanel.value))
})

onMounted(() => {
  cleanupReveal = revealAuthSurface(pageRoot.value)
})

onUnmounted(() => {
  cleanupReveal?.()
  if (countdownTimer) clearInterval(countdownTimer)
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

      <AuthModeTabs v-model="mode" :options="registerModes" data-auth-item />

      <div ref="formPanel" class="form-area" data-auth-item>
        <div v-if="mode === 'email'">
          <AuthTextInput
            v-model="email"
            label="邮箱"
            placeholder="name@qq.com"
            autocomplete="email"
            inputmode="email"
            @enter="handleRegister"
          >
            <template #prefix>邮箱</template>
          </AuthTextInput>
        </div>

        <div v-else>
          <AuthTextInput
            v-model="phone"
            label="手机号"
            placeholder="请输入手机号"
            autocomplete="tel"
            inputmode="tel"
            @enter="handleRegister"
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
            @enter="handleRegister"
          >
            <template #prefix>验证码</template>
            <template #action>
              <button class="inline-action" type="button" :disabled="countdown > 0" @click="handleSendCode">
                {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
              </button>
            </template>
          </AuthTextInput>
        </div>

        <AuthTextInput
          v-model="password"
          label="密码"
          :type="showPassword ? 'text' : 'password'"
          placeholder="至少 8 位"
          autocomplete="new-password"
          @enter="handleRegister"
        >
          <template #prefix>密码</template>
          <template #action>
            <button class="inline-action" type="button" @click="showPassword = !showPassword">
              {{ showPassword ? '隐藏' : '显示' }}
            </button>
          </template>
        </AuthTextInput>

        <AuthTextInput
          v-model="confirmPassword"
          label="确认密码"
          :type="showConfirm ? 'text' : 'password'"
          placeholder="再次输入密码"
          autocomplete="new-password"
          @enter="handleRegister"
        >
          <template #prefix>确认</template>
          <template #action>
            <button class="inline-action" type="button" @click="showConfirm = !showConfirm">
              {{ showConfirm ? '隐藏' : '显示' }}
            </button>
          </template>
        </AuthTextInput>

        <button class="primary-btn" type="button" :disabled="loading" @click="handleRegister">
          {{ loading ? '创建中...' : '创建账号' }}
        </button>
      </div>

      <div class="helper-row" data-auth-item>
        <span>已经有账号？</span>
        <button type="button" @click="router.push('/auth/signin')">返回登录</button>
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

.helper-row {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 18px;
  color: #667386;
  font-size: 0.9rem;
}

.helper-row button {
  padding: 0;
  border: 0;
  background: transparent;
  color: #0f6f88;
  font: inherit;
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

button:focus-visible,
a:focus-visible {
  outline: 3px solid rgba(15, 111, 136, 0.22);
  outline-offset: 2px;
}
</style>
