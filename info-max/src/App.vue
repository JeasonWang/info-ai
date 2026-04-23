<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { logoutUser } from '@/services/api'
import { clearUserSession, getSavedUser, getUserToken, USER_SESSION_CHANGED } from '@/services/userSession'

const user = ref(getSavedUser())
const userLabel = computed(() => user.value?.email ?? '未登录')

function refreshUser() {
  user.value = getSavedUser()
}

async function logout() {
  const token = getUserToken()
  if (token) {
    await logoutUser(token).catch(() => undefined)
  }
  clearUserSession()
  user.value = null
}

onMounted(() => {
  window.addEventListener(USER_SESSION_CHANGED, refreshUser)
})

onBeforeUnmount(() => {
  window.removeEventListener(USER_SESSION_CHANGED, refreshUser)
})
</script>

<template>
  <div class="app-shell">
    <header class="user-topbar">
      <RouterLink class="user-topbar__brand" to="/">Info Daren</RouterLink>
      <div class="user-topbar__account">
        <span>{{ userLabel }}</span>
        <button v-if="user" type="button" @click="logout">退出</button>
        <RouterLink v-else to="/login">登录</RouterLink>
      </div>
    </header>
    <main class="layout layout--flush">
      <RouterView />
    </main>
  </div>
</template>
