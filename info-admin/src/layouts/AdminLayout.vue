<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { adminUserStorage, clearAdminSession } from '@/stores/authStore'

const router = useRouter()
const user = adminUserStorage.get()

const navItems = [
  { to: '/dashboard', label: '总览' },
  { to: '/crawl-runs', label: '采集监控' },
  { to: '/data-quality', label: '数据质量' },
  { to: '/detail-jobs', label: '详情补偿' },
  { to: '/categories', label: '分类管理' },
  { to: '/channels', label: '渠道管理' },
  { to: '/audit-logs', label: '审计日志' },
]

async function logout() {
  clearAdminSession()
  await router.push({ name: 'login' })
}
</script>

<template>
  <main class="admin-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="eyebrow">INFO DAREN PRO</span>
        <h1>管理后台</h1>
      </div>
      <nav class="nav-list" aria-label="管理导航">
        <RouterLink v-for="item in navItems" :key="item.to" class="nav-item" :to="item.to">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">ADMIN CONSOLE</p>
          <h2>采集与质量中枢</h2>
        </div>
        <button class="ghost-button" type="button" @click="logout">
          {{ user?.email || '退出登录' }}
        </button>
      </header>
      <RouterView />
    </section>
  </main>
</template>
