<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import EventSummaryPanels from '@/components/EventSummaryPanels.vue'
import EventTimeline from '@/components/EventTimeline.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import { getEventById } from '@/services/api'
import type { EventDetail } from '@/types'
import { formatDateTime } from '@/utils'

const route = useRoute()
const loading = ref(false)
const error = ref('')
const detail = ref<EventDetail | null>(null)

const eventId = computed(() => Number(route.params.id))

async function loadDetail() {
  loading.value = true
  error.value = ''

  try {
    detail.value = await getEventById(eventId.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '事件详情加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadDetail)
</script>

<template>
  <div class="detail-page">
    <RouterLink class="button button--ghost detail-page__back" to="/">返回首页</RouterLink>

    <section v-if="loading" class="panel">
      <SkeletonBlock :lines="5" />
      <SkeletonBlock :lines="8" />
    </section>
    <section v-else-if="error" class="panel empty-state empty-state--rich">
      <strong>事件详情加载失败</strong>
      <p>{{ error }}</p>
      <button class="button button--ghost" type="button" @click="loadDetail">重新加载</button>
    </section>
    <template v-else-if="detail">
      <section class="panel detail-hero">
        <div class="tags">
          <span class="tag">{{ detail.event.primary_category.name }}</span>
          <span class="tag tag--soft">热度 {{ detail.event.heat_score }}</span>
          <span class="tag tag--soft">{{ formatDateTime(detail.event.last_updated_at) }}</span>
        </div>
        <h2>{{ detail.event.title }}</h2>
        <p class="detail-hero__summary">{{ detail.event.one_line_summary }}</p>
      </section>

      <EventTimeline :items="detail.timeline" />
      <EventSummaryPanels :summaries="detail.summaries" :source-views="detail.source_views" />

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Sources</p>
            <h2>代表性原始来源</h2>
          </div>
        </div>

        <div v-if="detail.representative_sources.length === 0" class="empty-state">
          暂时还没有代表性来源链接。
        </div>
        <div v-else class="source-link-list">
          <a
            v-for="source in detail.representative_sources"
            :key="source.info_id"
            class="source-link-card"
            :href="source.source_url"
            target="_blank"
            rel="noreferrer"
          >
            <strong>{{ source.title }}</strong>
            <span>{{ source.channel_name }}</span>
            <span class="panel__meta">{{ formatDateTime(source.event_time) }}</span>
          </a>
        </div>
      </section>
    </template>
  </div>
</template>
