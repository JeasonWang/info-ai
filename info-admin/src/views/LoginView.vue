<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loginAdmin } from '@/services/authApi'
import { adminTokenStorage, adminUserStorage } from '@/stores/authStore'

const router = useRouter()
const route = useRoute()
const email = ref('admin@info-daren.local')
const password = ref('')
const message = ref('')
const isSubmitting = ref(false)

async function handleSubmit() {
  isSubmitting.value = true
  message.value = '正在登录...'
  try {
    const result = await loginAdmin(email.value, password.value)
    adminTokenStorage.set(result.token)
    adminUserStorage.set(result.user)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : undefined
    await router.push(redirect || { name: 'dashboard' })
  } catch (error) {
    message.value = error instanceof Error ? error.message : '登录失败'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="login-shell">
    <section class="login-card">
      <p class="eyebrow">INFO DAREN MAX</p>
      <h1>管理后台登录</h1>
      <p class="login-copy">管理配置、采集监控和数据质量治理需要管理员身份。</p>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label>
          管理员邮箱
          <input v-model="email" type="email" autocomplete="username" />
        </label>
        <label>
          密码
          <input v-model="password" type="password" autocomplete="current-password" />
        </label>
        <button type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? '登录中' : '登录后台' }}
        </button>
      </form>
      <p class="form-message">{{ message }}</p>
    </section>
  </main>
</template>
