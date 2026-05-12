<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { adminUserStorage, clearAdminSession } from '@/stores/authStore'

const router = useRouter()
const route = useRoute()
const user = adminUserStorage.get()

const navGroups = [
  {
    title: '工作台',
    items: [{ to: '/dashboard', label: '首页总览' }],
  },
  {
    title: '采集中心',
    items: [
      { to: '/crawl-runs/health', label: '渠道健康' },
      { to: '/crawl-runs/runs', label: '运行日志' },
      { to: '/crawl-runs/tasks', label: '任务配置' },
      { to: '/crawl-runs/actions', label: '手动采集' },
      { to: '/detail-jobs/overview', label: '补偿总览' },
      { to: '/detail-jobs/pending', label: '待处理任务' },
      { to: '/detail-jobs/failed', label: '失败任务' },
    ],
  },
  {
    title: '质量治理',
    items: [
      { to: '/data-quality/report', label: '渠道质量' },
      { to: '/data-quality/snapshots', label: '质量快照' },
      { to: '/data-quality/event-analysis', label: '事件分析质量' },
      { to: '/data-quality/low-quality', label: '低质量内容' },
      { to: '/data-quality/actions', label: '治理工具' },
    ],
  },
  {
    title: '系统配置',
    items: [
      { to: '/channels', label: '渠道管理' },
      { to: '/credentials', label: '凭证管理' },
      { to: '/categories', label: '分类管理' },
      { to: '/llm-models', label: '大模型配置' },
      { to: '/audit-logs', label: '审计日志' },
    ],
  },
]

const currentTitle = computed(() => String(route.meta.title || '采集与质量中枢'))

async function logout() {
  clearAdminSession()
  await router.push({ name: 'login' })
}
</script>

<template>
  <main class="admin-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="eyebrow">INFO DAREN MAX</span>
        <h1>信息达人后台</h1>
      </div>
      <nav class="nav-list" aria-label="管理导航">
        <section v-for="group in navGroups" :key="group.title" class="nav-group">
          <span class="nav-group-title">{{ group.title }}</span>
          <RouterLink v-for="item in group.items" :key="item.to" class="nav-item" :to="item.to">
            {{ item.label }}
          </RouterLink>
        </section>
      </nav>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">首页 / {{ currentTitle }}</p>
          <h2>{{ currentTitle }}</h2>
        </div>
        <button class="ghost-button" type="button" @click="logout">
          {{ user?.email || '管理员' }} · 退出
        </button>
      </header>
      <RouterView />
    </section>
  </main>
</template>
