<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import DetailContent from '@/components/DetailContent.vue'
import FavoriteButton from '@/components/FavoriteButton.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import { useFavorites } from '@/composables/useFavorites'
import { getInfoById } from '@/services/api'
import type { InfoItem } from '@/types'
import { formatDateTime, getStatusTone } from '@/utils'

const route = useRoute()
const loading = ref(false)
const error = ref('')
const info = ref<InfoItem | null>(null)
const shareFeedback = ref('')
const { isFavorite, toggleFavorite } = useFavorites()

const infoId = computed(() => Number(route.params.id))

async function loadDetail() {
  loading.value = true
  error.value = ''

  try {
    info.value = await getInfoById(infoId.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '详情加载失败'
  } finally {
    loading.value = false
  }
}

async function handleShare() {
  if (!info.value || typeof window === 'undefined') return

  const sharePayload = {
    title: info.value.title,
    text: info.value.content,
    url: window.location.href,
  }

  try {
    if (navigator.share) {
      await navigator.share(sharePayload)
      shareFeedback.value = '分享面板已打开。'
    } else if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(window.location.href)
      shareFeedback.value = '详情链接已复制到剪贴板。'
    } else {
      shareFeedback.value = '当前环境不支持系统分享和剪贴板复制。'
    }
  } catch {
    shareFeedback.value = '分享未完成。'
  }
}

onMounted(loadDetail)
</script>

<template>
  <div class="detail-page">
    <RouterLink class="button button--ghost detail-page__back" to="/">返回看板</RouterLink>

    <section v-if="loading" class="panel">
      <SkeletonBlock :lines="5" />
      <SkeletonBlock :lines="8" />
    </section>
    <section v-else-if="error" class="panel empty-state empty-state--rich">
      <strong>详情加载失败</strong>
      <p>{{ error }}</p>
      <button class="button button--ghost" @click="loadDetail">重新加载</button>
    </section>
    <template v-else-if="info">
      <section class="panel detail-hero">
        <div class="tags">
          <span class="tag">{{ info.category_name }}</span>
          <span class="tag tag--soft">{{ info.channel_name }}</span>
          <span :class="['tag', `tag--${getStatusTone(info.detail_fetch_status)}`]">
            {{ info.detail_fetch_status }}
          </span>
        </div>
        <h2>{{ info.title }}</h2>
        <p class="detail-hero__summary">{{ info.content }}</p>

        <div class="detail-grid">
          <div>
            <span>事件时间</span>
            <strong>{{ formatDateTime(info.event_time || info.created_at) }}</strong>
          </div>
          <div>
            <span>核心主体</span>
            <strong>{{ info.core_entity || '暂无' }}</strong>
          </div>
          <div>
            <span>地点</span>
            <strong>{{ info.location || '暂无' }}</strong>
          </div>
          <div>
            <span>指标</span>
            <strong>{{ info.indicator_name ? `${info.indicator_name} ${info.indicator_value}` : '暂无' }}</strong>
          </div>
        </div>

        <div class="info-card__actions">
          <FavoriteButton :active="isFavorite(info.id)" @toggle="toggleFavorite(info.id)" />
          <button class="button button--ghost" @click="handleShare">分享</button>
          <a
            v-if="info.source_url"
            class="button button--primary"
            :href="info.source_url"
            target="_blank"
            rel="noreferrer"
          >
            打开原始来源
          </a>
        </div>
        <p v-if="shareFeedback" class="feedback">{{ shareFeedback }}</p>
      </section>

      <DetailContent :info="info" />
    </template>
  </div>
</template>
