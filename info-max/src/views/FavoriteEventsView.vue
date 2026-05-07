<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getFavoriteEvents } from '@/services/api'
import { getUserToken } from '@/services/userSession'
import type { FavoriteEventItem } from '@/types'
import { formatDateTime, summarize } from '@/utils'

const loading = ref(false)
const error = ref('')
const items = ref<FavoriteEventItem[]>([])
const requiresLogin = ref(false)

async function loadFavorites() {
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
    items.value = await getFavoriteEvents(token)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '收藏加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadFavorites)
</script>

<template>
  <main class="dashboard dashboard--events">
    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="panel__eyebrow">Favorites</p>
          <h1>我的收藏</h1>
        </div>
        <span class="panel__meta">最近 50 条</span>
      </div>

      <div v-if="requiresLogin" class="empty-state empty-state--rich">
        <strong>登录后可查看收藏</strong>
        <p>收藏的热点事件会集中放在这里，方便你稍后继续看。</p>
        <RouterLink class="button button--primary" to="/login">去登录</RouterLink>
      </div>

      <div v-else-if="loading" class="card-stack">
        <div class="history-card history-card--placeholder" />
        <div class="history-card history-card--placeholder" />
      </div>

      <div v-else-if="error" class="empty-state empty-state--rich">
        <strong>收藏加载失败</strong>
        <p>{{ error }}</p>
        <button class="button button--ghost" type="button" @click="loadFavorites">重新加载</button>
      </div>

      <div v-else-if="items.length === 0" class="empty-state empty-state--rich">
        <strong>暂时还没有收藏</strong>
        <p>打开事件详情页，点一下收藏，就能在这里快速找回。</p>
        <RouterLink class="button button--primary" to="/">返回首页</RouterLink>
      </div>

      <div v-else class="card-stack">
        <RouterLink
          v-for="item in items"
          :key="item.id"
          :to="item.target_path"
          class="history-card"
        >
          <div class="history-card__meta">
            <span class="tag tag--soft">事件</span>
            <span>{{ item.category_name }}</span>
            <span v-if="item.source_label">{{ item.source_label }}</span>
            <span>{{ formatDateTime(item.favorited_at) }}</span>
          </div>
          <strong>{{ item.title }}</strong>
          <p>{{ summarize(item.one_line_summary || '暂无摘要') }}</p>
        </RouterLink>
      </div>
    </section>
  </main>
</template>
