<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser, registerUser } from '@/services/api'
import { saveUserSession } from '@/services/userSession'

const router = useRouter()
const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const message = ref('')
const isSubmitting = ref(false)

async function submitAuth() {
  isSubmitting.value = true
  message.value = mode.value === 'login' ? '正在登录...' : '正在注册...'
  try {
    if (mode.value === 'register') {
      await registerUser(email.value, password.value)
      mode.value = 'login'
      message.value = '注册成功，请登录'
      return
    }
    const result = await loginUser(email.value, password.value)
    saveUserSession(result.token, result.user)
    await router.push({ name: 'home' })
  } catch (error) {
    message.value = error instanceof Error ? error.message : '操作失败'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="dashboard auth-dashboard">
    <section class="panel auth-card">
      <p class="panel__eyebrow">Account</p>
      <h1>{{ mode === 'login' ? '登录信息达人' : '注册账号' }}</h1>
      <p class="auth-copy">不登录也可以浏览热点；登录后可同步收藏、首页筛选偏好和阅读历史，后续继续开放关注主题。</p>

      <form class="auth-form" @submit.prevent="submitAuth">
        <input v-model="email" type="email" autocomplete="username" placeholder="邮箱" />
        <input v-model="password" type="password" autocomplete="current-password" placeholder="密码，至少 8 位" />
        <button class="button button--primary" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? '处理中' : mode === 'login' ? '登录' : '注册' }}
        </button>
      </form>

      <button class="auth-switch" type="button" @click="mode = mode === 'login' ? 'register' : 'login'">
        {{ mode === 'login' ? '还没有账号？去注册' : '已有账号？去登录' }}
      </button>
      <p class="auth-message">{{ message }}</p>
    </section>
  </main>
</template>
