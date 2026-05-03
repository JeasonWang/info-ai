<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth'

const { login, register } = useAuth()
const isRegister = ref(false)
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const emailError = ref('')
const passwordError = ref('')

function validateEmail(value: string): boolean {
  emailError.value = ''
  if (!value) {
    emailError.value = '请输入邮箱'
    return false
  }
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!re.test(value)) {
    emailError.value = '邮箱格式不正确'
    return false
  }
  return true
}

function validatePassword(value: string): boolean {
  passwordError.value = ''
  if (!value) {
    passwordError.value = '请输入密码'
    return false
  }
  if (value.length < 6) {
    passwordError.value = '密码至少6位'
    return false
  }
  return true
}

async function submit() {
  const emailValid = validateEmail(email.value)
  const passwordValid = validatePassword(password.value)
  if (!emailValid || !passwordValid) return

  if (isRegister.value) {
    if (password.value !== confirmPassword.value) {
      uni.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }
  }

  submitting.value = true
  try {
    if (isRegister.value) {
      await register(email.value, password.value)
      uni.showToast({ title: '注册成功', icon: 'success' })
    } else {
      await login(email.value, password.value)
      uni.showToast({ title: '登录成功', icon: 'success' })
    }
    setTimeout(() => {
      uni.reLaunch({ url: '/pages/home/home' })
    }, 800)
  } catch {
    // error handled by request interceptor
  } finally {
    submitting.value = false
  }
}

function toggleMode() {
  isRegister.value = !isRegister.value
  emailError.value = ''
  passwordError.value = ''
}
</script>

<template>
  <view class="login-page">
    <view class="hero">
      <text class="hero-icon">&#xe60f;</text>
      <text class="hero-title">InfoMVP</text>
      <text class="hero-subtitle">热点事件聚合平台</text>
    </view>

    <view class="form-card">
      <text class="form-title">{{ isRegister ? '注册账号' : '欢迎回来' }}</text>

      <view class="field">
        <view class="input-wrap">
          <text class="input-icon">&#xe619;</text>
          <input
            v-model="email"
            class="input"
            :class="{ 'input--error': emailError }"
            type="text"
            placeholder="邮箱"
            @blur="validateEmail(email)"
          />
        </view>
        <text v-if="emailError" class="error-msg">{{ emailError }}</text>
      </view>

      <view class="field">
        <view class="input-wrap">
          <text class="input-icon">&#xe618;</text>
          <input
            v-model="password"
            class="input"
            :class="{ 'input--error': passwordError }"
            type="password"
            placeholder="密码（至少6位）"
            @blur="validatePassword(password)"
          />
        </view>
        <text v-if="passwordError" class="error-msg">{{ passwordError }}</text>
      </view>

      <view v-if="isRegister" class="field">
        <view class="input-wrap">
          <text class="input-icon">&#xe618;</text>
          <input
            v-model="confirmPassword"
            class="input"
            type="password"
            placeholder="确认密码"
          />
        </view>
      </view>

      <button
        class="submit-btn"
        :loading="submitting"
        :disabled="submitting"
        @click="submit"
      >
        {{ isRegister ? '注册' : '登录' }}
      </button>

      <text class="toggle" @click="toggleMode">
        {{ isRegister ? '已有账号？去登录' : '还没有账号？去注册' }}
      </text>
    </view>
  </view>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: var(--bg-color);
  display: flex;
  flex-direction: column;
}

.hero {
  background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
  padding: 80rpx 40rpx 60rpx;
  border-radius: 0 0 40rpx 40rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  overflow: hidden;
  border-bottom: 1rpx solid var(--divider);
}

.hero::before {
  content: '';
  position: absolute;
  top: -40%;
  right: -20%;
  width: 400rpx;
  height: 400rpx;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.08) 0%, transparent 70%);
  pointer-events: none;
}

.hero-icon {
  font-family: 'uniicons';
  font-size: 64rpx;
  color: var(--brand-accent);
  margin-bottom: 16rpx;
  position: relative;
  z-index: 1;
}

.hero-title {
  font-size: 48rpx;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 2rpx;
  margin-bottom: 8rpx;
  position: relative;
  z-index: 1;
}

.hero-subtitle {
  font-size: 26rpx;
  color: var(--text-muted);
  position: relative;
  z-index: 1;
}

.form-card {
  flex: 1;
  margin: -32rpx 24rpx 24rpx;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 48rpx 40rpx;
  box-shadow: var(--shadow-md);
  position: relative;
  z-index: 2;
}

.form-title {
  display: block;
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 40rpx;
  text-align: center;
}

.field {
  margin-bottom: 8rpx;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 12rpx;
  width: 100%;
  height: 88rpx;
  border: 1rpx solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0 20rpx;
  box-sizing: border-box;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  background: var(--bg-color);
}

.input-wrap:focus-within {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3rpx rgba(37, 99, 235, 0.1);
}

.input-icon {
  font-family: 'uniicons';
  font-size: 28rpx;
  color: var(--text-muted);
}

.input {
  flex: 1;
  height: 88rpx;
  font-size: var(--text-base);
  color: var(--text-primary);
  background: transparent;
}

.input::placeholder {
  color: var(--text-muted);
}

.input--error {
  border-color: var(--danger-color, #ef4444);
}

.error-msg {
  display: block;
  font-size: var(--text-xs);
  color: var(--danger-color, #ef4444);
  margin-top: 8rpx;
  padding-left: 8rpx;
}

.submit-btn {
  width: 100%;
  height: 88rpx;
  background: var(--brand-accent);
  color: #fff;
  border-radius: var(--radius-pill);
  font-size: var(--text-lg);
  font-weight: 600;
  margin-top: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 1;
  box-shadow: 0 8rpx 24rpx rgba(37, 99, 235, 0.25);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.submit-btn:active {
  transform: scale(0.98);
  box-shadow: 0 4rpx 12rpx rgba(37, 99, 235, 0.2);
}

.submit-btn[disabled] {
  opacity: 0.6;
}

.toggle {
  display: block;
  text-align: center;
  margin-top: 32rpx;
  font-size: var(--text-sm);
  color: var(--brand-accent);
}
</style>
