<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EventTimeline from '@/components/EventTimeline.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import { useEventFavorites } from '@/composables/useEventFavorites'
import { getEventById, recordReadHistory } from '@/services/api'
import { getUserToken } from '@/services/userSession'
import type { EventDetail, EventTimelineItem } from '@/types'
import { formatDateTime } from '@/utils'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const detail = ref<EventDetail | null>(null)
const favoriteFeedback = ref('')
const { isFavorite, syncFavoritesFromServer, toggleFavorite } = useEventFavorites()

const eventId = computed(() => Number(route.params.id))
function normalizeText(text?: string | null) {
  return (text || '').replace(/\s+/g, ' ').trim()
}

function isRedundantText(text: string, references: string[]) {
  const current = normalizeText(text)
  if (!current) {
    return true
  }
  return references.some((reference) => {
    const normalizedReference = normalizeText(reference)
    if (!normalizedReference) {
      return false
    }
    return current === normalizedReference || current.includes(normalizedReference) || normalizedReference.includes(current)
  })
}

const hasTechContext = computed(() => {
  const techContext = detail.value?.tech_context
  if (!techContext) {
    return false
  }
  return techContext.topics.length > 0 || techContext.entities.length > 0 || techContext.keywords.length > 0
})
const valuableTimeline = computed<EventTimelineItem[]>(() => {
  if (!detail.value) {
    return []
  }
  const references = [
    detail.value.event.title,
    detail.value.event.one_line_summary,
    focusConclusion.value,
    focusLatestUpdate.value,
  ]
  const result: EventTimelineItem[] = []
  const seen: string[] = []
  detail.value.timeline.forEach((item) => {
    if (isRedundantText(item.summary, [...references, ...seen])) {
      return
    }
    result.push(item)
    seen.push(item.summary)
  })
  return result
})

function formatTechTopicType(topicType: string) {
  const topicMap: Record<string, string> = {
    chip_release: '芯片发布',
    model_release: '模型发布',
    dev_tool: '开发工具',
    general_tech: '通用科技',
  }

  return topicMap[topicType] ?? topicType
}

function formatTechList(items?: string[]) {
  if (!items || items.length === 0) {
    return []
  }
  return items
}
const focusConclusion = computed(() => {
  if (!detail.value) {
    return '暂时还没有提炼出重点结论。'
  }
  return detail.value.summaries.what_happened || detail.value.event.one_line_summary || '暂时还没有提炼出重点结论。'
})
const focusLatestUpdate = computed(() => {
  if (!detail.value) {
    return '暂时还没有最新进展摘要。'
  }

  const latestUpdate = (detail.value.summaries.latest_update || '').trim()
  const whatHappened = (detail.value.summaries.what_happened || '').trim()
  if (!latestUpdate) {
    return '暂时还没有最新进展摘要。'
  }
  if (latestUpdate === whatHappened) {
    return '当前暂无额外新增进展，事件仍在持续跟进。'
  }
  return latestUpdate
})

async function loadDetail() {
  loading.value = true
  error.value = ''

  try {
    detail.value = await getEventById(eventId.value)
    const token = getUserToken()
    if (token) {
      await recordReadHistory(token, { eventId: eventId.value }).catch(() => undefined)
    }
    try {
      await syncFavoritesFromServer()
    } catch {
      // 收藏是登录增强能力，同步失败不应该阻断热点详情阅读。
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '事件详情加载失败'
  } finally {
    loading.value = false
  }
}

function handleBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/')
}

async function handleFavorite() {
  if (!detail.value) return

  favoriteFeedback.value = ''
  try {
    await toggleFavorite(detail.value.event.id)
  } catch (err) {
    favoriteFeedback.value = err instanceof Error ? err.message : '收藏同步失败，请稍后再试'
  }
}

onMounted(loadDetail)
</script>

<template>
  <div class="detail-page">
    <button class="detail-back-link" type="button" data-testid="back-button" @click="handleBack">
      返回
    </button>

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
      <section class="panel detail-hero" data-testid="event-detail-hero">
        <div class="detail-hero__core" data-testid="event-detail-core">
          <p class="detail-hero__meta-line" data-testid="event-detail-meta">
            {{ detail.event.primary_category.name }} · {{ formatDateTime(detail.event.last_updated_at) }} ·
            {{ detail.representative_sources.length }} 个来源
          </p>
          <h2>{{ detail.event.title }}</h2>
          <div class="detail-hero__quickfacts" data-testid="event-detail-quickfacts">
            <span>热度 {{ detail.event.heat_score }}</span>
            <span v-if="detail.event.composite_score !== undefined">综合 {{ detail.event.composite_score }}</span>
            <span>来源 {{ detail.event.source_count ?? detail.representative_sources.length }}</span>
            <span v-if="detail.event.last_updated_at">更新 {{ formatDateTime(detail.event.last_updated_at) }}</span>
          </div>
        </div>
        <div class="detail-utility-actions detail-utility-actions--event">
          <button
            type="button"
            class="detail-utility-action"
            data-testid="event-favorite-button"
            @click="handleFavorite"
          >
            {{ isFavorite(detail.event.id) ? '已收藏' : '收藏' }}
          </button>
        </div>
        <p v-if="favoriteFeedback" class="feedback">{{ favoriteFeedback }}</p>

        <div class="detail-hero__support" data-testid="event-detail-support">
          <article class="detail-focus-card detail-focus-card--primary detail-focus-card--lead">
            <p class="detail-focus-card__label">重点结论</p>
            <p class="detail-focus-card__body">
              {{ focusConclusion }}
            </p>
          </article>
          <div class="detail-insight-list">
            <article class="detail-insight-row">
              <p class="detail-focus-card__label">最新进展</p>
              <p class="detail-focus-card__body">
                {{ focusLatestUpdate }}
              </p>
            </article>
            <article class="detail-insight-row">
              <p class="detail-focus-card__label">为什么重要</p>
              <p class="detail-focus-card__body">
                {{ detail.summaries.why_it_matters || '暂时还没有重要性摘要。' }}
              </p>
            </article>
          </div>
        </div>
      </section>

      <section v-if="hasTechContext" class="panel" data-testid="event-tech-context">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Tech Context</p>
            <h2>技术上下文</h2>
          </div>
        </div>
        <div class="detail-focus-grid">
          <article class="detail-focus-card">
            <p class="detail-focus-card__label">主题聚合</p>
            <div class="tags">
              <span
                v-for="item in detail.tech_context.topics"
                :key="`${item.topic_type}-${item.count}`"
                class="tag tag--soft"
              >
                {{ formatTechTopicType(item.topic_type) }} {{ item.count }}
              </span>
            </div>
          </article>
          <article v-if="detail.tech_context.entities.length > 0" class="detail-focus-card">
            <p class="detail-focus-card__label">关键实体</p>
            <div class="tags">
              <span
                v-for="item in formatTechList(detail.tech_context.entities)"
                :key="item"
                class="tag tag--soft"
              >
                {{ item }}
              </span>
            </div>
          </article>
          <article v-if="detail.tech_context.keywords.length > 0" class="detail-focus-card">
            <p class="detail-focus-card__label">关键词</p>
            <div class="tags">
              <span
                v-for="item in formatTechList(detail.tech_context.keywords)"
                :key="item"
                class="tag tag--soft"
              >
                {{ item }}
              </span>
            </div>
          </article>
        </div>
      </section>

      <div v-if="valuableTimeline.length > 0" id="event-timeline-section">
        <EventTimeline :items="valuableTimeline" />
      </div>

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
