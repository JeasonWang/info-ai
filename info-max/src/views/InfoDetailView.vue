<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DetailContent from '@/components/DetailContent.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import { useFavorites } from '@/composables/useFavorites'
import { getInfoById, recordReadHistory } from '@/services/api'
import { getUserToken } from '@/services/userSession'
import type { InfoItem } from '@/types'
import { formatDateTime } from '@/utils'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const info = ref<InfoItem | null>(null)
const shareFeedback = ref('')
const { isFavorite, toggleFavorite } = useFavorites()

const infoId = computed(() => Number(route.params.id))

function normalizeReadableText(text?: string | null) {
  return (text || '').replace(/\s+/g, ' ').trim()
}

function isRepeatedText(text: string, references: string[]) {
  const current = normalizeReadableText(text)
  if (!current) {
    return true
  }
  return references.some((reference) => {
    const normalizedReference = normalizeReadableText(reference)
    if (!normalizedReference) {
      return false
    }
    if (current === normalizedReference || normalizedReference.includes(current)) {
      return true
    }
    // 正文句子经常会以标题开头，只要后面有新增信息，就应该保留给用户阅读。
    return current.includes(normalizedReference) && current.length - normalizedReference.length <= 6
  })
}

function splitReadableParagraphs(content: string) {
  return content
    .replace(/\r\n/g, '\n')
    .split(/\n+/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
}

const readableParagraphs = computed(() => {
  if (!info.value) {
    return []
  }

  const references = [info.value.title]
  const paragraphs = splitReadableParagraphs(info.value.content)
  const result: string[] = []

  paragraphs.forEach((paragraph) => {
    if (isRepeatedText(paragraph, [...references, ...result])) {
      return
    }
    result.push(paragraph)
  })

  return result
})

const readableContent = computed(() => readableParagraphs.value.join('\n\n'))

const leadSummary = computed(() => {
  if (!info.value || readableParagraphs.value.length < 2) {
    return ''
  }

  const firstParagraph = readableParagraphs.value[0]
  if (isRepeatedText(firstParagraph, [info.value.title]) || firstParagraph.includes(info.value.title)) {
    return ''
  }
  return firstParagraph.length > 120 ? `${firstParagraph.slice(0, 120)}...` : firstParagraph
})

const quickFacts = computed(() => {
  if (!info.value) {
    return []
  }
  return [
    info.value.channel_name,
    formatDateTime(info.value.event_time || info.value.created_at),
    `质量评分 ${info.value.detail_score}`,
    `正文长度 ${info.value.detail_content_length}`,
  ].filter((item): item is string => Boolean(item))
})

const bodyContent = computed(() => {
  if (!leadSummary.value) {
    return readableContent.value
  }
  return readableParagraphs.value.slice(1).join('\n\n')
})

async function loadDetail() {
  loading.value = true
  error.value = ''

  try {
    info.value = await getInfoById(infoId.value)
    const token = getUserToken()
    if (token) {
      await recordReadHistory(token, { infoId: infoId.value }).catch(() => undefined)
    }
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

function handleBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/')
}

function handleFavorite() {
  if (!info.value) return
  toggleFavorite(info.value.id)
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
      <strong>详情加载失败</strong>
      <p>{{ error }}</p>
      <button class="button button--ghost" @click="loadDetail">重新加载</button>
    </section>
    <template v-else-if="info">
      <section class="panel detail-hero" data-testid="info-detail-hero">
        <div class="detail-hero__core">
          <p class="detail-hero__meta-line" data-testid="info-detail-meta-line">
            {{ info.category_name }} · {{ info.channel_name }} · {{ formatDateTime(info.event_time || info.created_at) }}
          </p>
          <h2>{{ info.title }}</h2>
          <div class="detail-hero__quickfacts" data-testid="info-detail-quickfacts">
            <span v-for="item in quickFacts" :key="item" class="detail-hero__quickfact">
              {{ item }}
            </span>
          </div>
        </div>

        <div class="detail-utility-actions">
          <button type="button" class="detail-utility-action" @click="handleFavorite">
            {{ isFavorite(info.id) ? '已收藏' : '收藏' }}
          </button>
          <button type="button" class="detail-utility-action" @click="handleShare">分享</button>
          <a
            v-if="info.source_url"
            class="detail-utility-action"
            :href="info.source_url"
            target="_blank"
            rel="noreferrer"
          >
            打开原始来源
          </a>
        </div>
        <p v-if="shareFeedback" class="feedback">{{ shareFeedback }}</p>

        <article
          v-if="leadSummary"
          class="detail-focus-card detail-focus-card--primary detail-focus-card--lead"
          data-testid="info-detail-summary-card"
        >
          <p class="detail-focus-card__label">先看重点</p>
          <p class="detail-focus-card__body">{{ leadSummary }}</p>
        </article>
      </section>

      <DetailContent :info="info" :content="bodyContent" />
    </template>
  </div>
</template>
