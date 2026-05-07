<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getReadHistory } from '@/services/api'
import { getUserToken } from '@/services/userSession'
import type { ReadHistoryItem } from '@/types'
import { formatDateTime, summarize } from '@/utils'

const loading = ref(false)
const error = ref('')
const items = ref<ReadHistoryItem[]>([])
const requiresLogin = ref(false)

async function loadHistory() {
  const token = getUserToken()
  if (!token) {
    requiresLogin.value = true
    items.value = []
    return
  }

  loading.value = true
  error.value = ''
  requiresLogin.value = false

  try {
    items.value = await getReadHistory(token)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '阅读历史加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadHistory)
</script>

<template>
  <main class="dashboard dashboard--events">
    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="panel__eyebrow">History</p>
          <h1>阅读历史</h1>
        </div>
        <span class="panel__meta">最近 50 条</span>
      </div>

      <div v-if="requiresLogin" class="empty-state empty-state--rich">
        <strong>登录后可查看阅读历史</strong>
        <p>我们会自动记录你最近看过的事件和资讯，方便你快速继续阅读。</p>
        <RouterLink class="button button--primary" to="/login">去登录</RouterLink>
      </div>

      <div v-else-if="loading" class="card-stack">
        <div class="history-card history-card--placeholder" />
        <div class="history-card history-card--placeholder" />
      </div>

      <div v-else-if="error" class="empty-state empty-state--rich">
        <strong>阅读历史加载失败</strong>
        <p>{{ error }}</p>
        <button class="button button--ghost" type="button" @click="loadHistory">重新加载</button>
      </div>

      <div v-else-if="items.length === 0" class="empty-state empty-state--rich">
        <strong>暂时还没有阅读历史</strong>
        <p>去首页看看热点，读过的内容会自动记录在这里。</p>
        <RouterLink class="button button--primary" to="/">返回首页</RouterLink>
      </div>

      <div v-else class="card-stack">
        <RouterLink
          v-for="item in items"
          :key="`${item.item_type}-${item.event_id ?? item.info_id}`"
          :to="item.target_path"
          class="history-card"
        >
          <div class="history-card__meta">
            <span class="tag tag--soft">{{ item.item_type === 'event' ? '事件' : '资讯' }}</span>
            <span>{{ item.subtitle }}</span>
            <span v-if="item.source_label">{{ item.source_label }}</span>
            <span>{{ formatDateTime(item.read_at) }}</span>
          </div>
          <strong>{{ item.title }}</strong>
          <p>{{ summarize(item.primary_remark || '暂无摘要') }}</p>
        </RouterLink>
      </div>
    </section>
  </main>
</template>
