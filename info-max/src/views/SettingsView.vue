<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  createCategory,
  createChannel,
  getAdminCategories,
  getAdminChannels,
  getInfos,
  rebuildEvents,
  triggerCrawl,
  updateCategory,
  updateChannel,
} from '@/services/api'
import type { Category, CategoryPayload, Channel, ChannelPayload, InfoItem } from '@/types'

const categories = ref<Category[]>([])
const channels = ref<Channel[]>([])
const acquisitionInfos = ref<InfoItem[]>([])
const loading = ref(false)
const saving = ref(false)
const rebuilding = ref(false)
const crawlingChannelCode = ref('')
const message = ref('')
const error = ref('')
const editingCategoryId = ref<number | null>(null)
const editingChannelId = ref<number | null>(null)

const categoryForm = reactive<CategoryPayload>({
  name: '',
  code: '',
  description: '',
})

const channelForm = reactive<ChannelPayload>({
  name: '',
  code: '',
  base_url: '',
  category_id: 0,
  crawl_interval: 60,
  is_active: 1,
})

const editCategoryForm = reactive<CategoryPayload>({
  name: '',
  code: '',
  description: '',
})

const editChannelForm = reactive<ChannelPayload>({
  name: '',
  code: '',
  base_url: '',
  category_id: 0,
  crawl_interval: 60,
  is_active: 1,
})

const hasCategoryOptions = computed(() => categories.value.length > 0)
const acquisitionStatusSummary = computed(() => {
  const summaryMap = {
    complete: 0,
    partial: 0,
    list_only: 0,
    failed: 0,
  }

  acquisitionInfos.value.forEach((info) => {
    if (info.detail_fetch_status in summaryMap) {
      summaryMap[info.detail_fetch_status as keyof typeof summaryMap] += 1
    }
  })

  return [
    { key: 'complete', label: '完整详情', count: summaryMap.complete, tone: 'success' },
    { key: 'partial', label: '部分详情', count: summaryMap.partial, tone: 'warning' },
    { key: 'list_only', label: '仅列表摘要', count: summaryMap.list_only, tone: 'soft' },
    { key: 'failed', label: '抓取失败', count: summaryMap.failed, tone: 'danger' },
  ]
})
const acquisitionAverageScore = computed(() => {
  if (acquisitionInfos.value.length === 0) {
    return '0.0'
  }

  const totalScore = acquisitionInfos.value.reduce((sum, info) => sum + (info.detail_score || 0), 0)
  return (totalScore / acquisitionInfos.value.length).toFixed(1)
})
const acquisitionTrendSnapshot = computed(() => {
  if (acquisitionInfos.value.length === 0) {
    return null
  }

  const midpoint = Math.ceil(acquisitionInfos.value.length / 2)
  const recentBatch = acquisitionInfos.value.slice(0, midpoint)
  const earlierBatch = acquisitionInfos.value.slice(midpoint)

  const averageScore = (items: InfoItem[]) => {
    if (items.length === 0) {
      return 0
    }
    return items.reduce((sum, info) => sum + (info.detail_score || 0), 0) / items.length
  }

  const completeRate = (items: InfoItem[]) => {
    if (items.length === 0) {
      return 0
    }
    return items.filter((info) => info.detail_fetch_status === 'complete').length / items.length
  }

  const failedRate = (items: InfoItem[]) => {
    if (items.length === 0) {
      return 0
    }
    return items.filter((info) => info.detail_fetch_status === 'failed').length / items.length
  }

  const recentScore = averageScore(recentBatch)
  const earlierScore = averageScore(earlierBatch)
  const recentCompleteRate = completeRate(recentBatch)
  const earlierCompleteRate = completeRate(earlierBatch)
  const recentFailedRate = failedRate(recentBatch)
  const earlierFailedRate = failedRate(earlierBatch)

  return {
    recentSize: recentBatch.length,
    earlierSize: earlierBatch.length,
    scoreDelta: recentScore - earlierScore,
    completeDelta: recentCompleteRate - earlierCompleteRate,
    failedDelta: recentFailedRate - earlierFailedRate,
    recentScore: recentScore.toFixed(1),
    earlierScore: earlierScore.toFixed(1),
  }
})
const acquisitionChannelTrends = computed(() => {
  const grouped = new Map<string, InfoItem[]>()

  acquisitionInfos.value.forEach((info) => {
    const channelName = info.channel_name || '未知渠道'
    const items = grouped.get(channelName) || []
    items.push(info)
    grouped.set(channelName, items)
  })

  const averageScore = (items: InfoItem[]) => {
    if (items.length === 0) {
      return 0
    }
    return items.reduce((sum, info) => sum + (info.detail_score || 0), 0) / items.length
  }

  const failedRate = (items: InfoItem[]) => {
    if (items.length === 0) {
      return 0
    }
    return items.filter((info) => info.detail_fetch_status === 'failed').length / items.length
  }

  return [...grouped.entries()]
    .map(([channelName, items]) => {
      const midpoint = Math.ceil(items.length / 2)
      const recentBatch = items.slice(0, midpoint)
      const earlierBatch = items.slice(midpoint)
      return {
        channelName,
        scoreDelta: averageScore(recentBatch) - averageScore(earlierBatch),
        failedDelta: failedRate(recentBatch) - failedRate(earlierBatch),
        recentSize: recentBatch.length,
        earlierSize: earlierBatch.length,
      }
    })
    .sort((left, right) => Math.abs(right.scoreDelta) - Math.abs(left.scoreDelta))
    .slice(0, 3)
})
const acquisitionTopError = computed(() => {
  if (acquisitionErrorDistribution.value.length === 0) {
    return null
  }
  return acquisitionErrorDistribution.value[0]
})
const acquisitionTopStrategy = computed(() => {
  if (acquisitionStrategyDistribution.value.length === 0) {
    return null
  }
  return acquisitionStrategyDistribution.value[0]
})
const acquisitionTopicDistribution = computed(() => {
  const topicCounter = new Map<string, number>()

  acquisitionInfos.value.forEach((info) => {
    if (!info.tech_topic_type) {
      return
    }
    topicCounter.set(info.tech_topic_type, (topicCounter.get(info.tech_topic_type) || 0) + 1)
  })

  return [...topicCounter.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3)
    .map(([topicType, count]) => ({ topicType, count }))
})
const acquisitionKeywordDistribution = computed(() => {
  const keywordCounter = new Map<string, number>()

  acquisitionInfos.value.forEach((info) => {
    info.tech_keywords?.forEach((keyword) => {
      keywordCounter.set(keyword, (keywordCounter.get(keyword) || 0) + 1)
    })
  })

  return [...keywordCounter.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 5)
    .map(([keyword, count]) => ({ keyword, count }))
})
const acquisitionErrorDistribution = computed(() => {
  const errorCounter = new Map<string, number>()

  acquisitionInfos.value.forEach((info) => {
    if (!info.detail_fetch_error) {
      return
    }

    errorCounter.set(info.detail_fetch_error, (errorCounter.get(info.detail_fetch_error) || 0) + 1)
  })

  // 只展示前几项高频失败原因，方便快速诊断当前最值得优先处理的问题。
  return [...errorCounter.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3)
    .map(([errorCode, count]) => ({ errorCode, count }))
})
const acquisitionStrategyDistribution = computed(() => {
  const strategyCounter = new Map<string, number>()

  acquisitionInfos.value.forEach((info) => {
    const strategy = info.detail_strategy || '未记录'
    strategyCounter.set(strategy, (strategyCounter.get(strategy) || 0) + 1)
  })

  // 保留主力策略外，再展示次级策略，帮助判断当前回退是否过于频繁。
  return [...strategyCounter.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3)
    .map(([strategy, count]) => ({ strategy, count }))
})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    // 管理页同时拉取一批最近采集结果，方便快速观察质量趋势和失败主因。
    const [categoryData, channelData, infoData] = await Promise.all([
      getAdminCategories(),
      getAdminChannels(),
      getInfos({ page: 1, page_size: 20 }),
    ])
    categories.value = categoryData
    channels.value = channelData
    acquisitionInfos.value = infoData.items

    if (!channelForm.category_id && categoryData.length > 0) {
      channelForm.category_id = categoryData[0].id
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载配置失败'
  } finally {
    loading.value = false
  }
}

function resetCategoryForm() {
  categoryForm.name = ''
  categoryForm.code = ''
  categoryForm.description = ''
}

function resetChannelForm() {
  channelForm.name = ''
  channelForm.code = ''
  channelForm.base_url = ''
  channelForm.crawl_interval = 60
  channelForm.is_active = 1

  if (categories.value.length > 0) {
    channelForm.category_id = categories.value[0].id
  }
}

async function handleCreateCategory() {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    await createCategory({ ...categoryForm })
    message.value = '分类已创建'
    resetCategoryForm()
    await loadData()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建分类失败'
  } finally {
    saving.value = false
  }
}

async function handleCreateChannel() {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    await createChannel({ ...channelForm })
    message.value = '渠道已创建'
    resetChannelForm()
    await loadData()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建渠道失败'
  } finally {
    saving.value = false
  }
}

function startEditCategory(category: Category) {
  editingCategoryId.value = category.id
  editCategoryForm.name = category.name
  editCategoryForm.code = category.code
  editCategoryForm.description = category.description
}

function startEditChannel(channel: Channel) {
  editingChannelId.value = channel.id
  editChannelForm.name = channel.name
  editChannelForm.code = channel.code
  editChannelForm.base_url = channel.base_url
  editChannelForm.category_id = channel.category_id
  editChannelForm.crawl_interval = channel.crawl_interval
  editChannelForm.is_active = channel.is_active
}

async function handleUpdateCategory(id: number) {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    await updateCategory(id, { ...editCategoryForm })
    message.value = '分类已更新'
    editingCategoryId.value = null
    await loadData()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '更新分类失败'
  } finally {
    saving.value = false
  }
}

async function handleUpdateChannel(id: number) {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    await updateChannel(id, { ...editChannelForm })
    message.value = '渠道已更新'
    editingChannelId.value = null
    await loadData()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '更新渠道失败'
  } finally {
    saving.value = false
  }
}

async function handleRebuildEvents() {
  rebuilding.value = true
  message.value = ''
  error.value = ''
  try {
    const result = await rebuildEvents()
    message.value = `事件已重建，共生成 ${result.event_count} 个事件`
  } catch (err) {
    error.value = err instanceof Error ? err.message : '事件重建失败'
  } finally {
    rebuilding.value = false
  }
}

async function handleTriggerCrawl(channelCode: string) {
  crawlingChannelCode.value = channelCode
  message.value = ''
  error.value = ''
  try {
    const crawlResult = await triggerCrawl(channelCode)
    const rebuildResult = await rebuildEvents()
    message.value =
      `${crawlResult.channel} 抓取完成：原始 ${crawlResult.raw_count} 条，清洗后 ${crawlResult.cleaned_count} 条，详情补全 ${crawlResult.detail_fetched} 条；事件流已刷新，共生成 ${rebuildResult.event_count} 个事件`
  } catch (err) {
    error.value = err instanceof Error ? err.message : '手动抓取失败'
  } finally {
    crawlingChannelCode.value = ''
  }
}

function formatQualityStatus(status: string) {
  const statusMap: Record<string, string> = {
    pending: '待抓取',
    list_only: '仅列表摘要',
    partial: '部分详情',
    complete: '完整详情',
    failed: '抓取失败',
  }
  return statusMap[status] ?? status
}

function formatQualityError(errorCode: string) {
  const errorMap: Record<string, string> = {
    anti_crawl_blocked: '反爬拦截',
    shell_page: '壳页面',
    content_too_short: '正文过短',
    weak_relevance: '内容弱相关',
    detail_unavailable: '详情不可用',
    invalid_topic_payload: '话题数据异常',
    network_timeout: '请求超时',
  }
  return errorMap[errorCode] ?? errorCode
}

function formatTechKeywords(keywords?: string[] | null) {
  if (!keywords || keywords.length === 0) {
    return []
  }
  return keywords
}

function formatTechEntities(entities?: string[] | null) {
  if (!entities || entities.length === 0) {
    return []
  }
  return entities
}

function formatTechTopicType(topicType?: string | null) {
  const topicMap: Record<string, string> = {
    chip_release: '芯片发布',
    model_release: '模型发布',
    dev_tool: '开发工具',
    general_tech: '通用科技',
  }

  if (!topicType) {
    return '未识别'
  }
  return topicMap[topicType] ?? topicType
}

function formatTrendDelta(delta: number, suffix = '') {
  const rounded = Math.abs(delta)
  const formatted = suffix === '%'
    ? `${(rounded * 100).toFixed(0)}${suffix}`
    : rounded.toFixed(1)

  if (delta > 0) {
    return `上升 ${formatted}`
  }
  if (delta < 0) {
    return `下降 ${formatted}`
  }
  return `持平 ${formatted}`
}

onMounted(loadData)
</script>

<template>
  <div class="settings-page">
    <div class="settings-page__top">
      <div>
        <p class="panel__eyebrow">Admin</p>
        <h1>配置管理</h1>
        <p class="panel__meta">管理分类和渠道配置，并在需要时手动触发抓取与事件重建。</p>
      </div>
      <RouterLink class="button button--ghost" to="/">返回首页</RouterLink>
    </div>

    <p v-if="message" class="feedback">{{ message }}</p>
    <p v-if="error" class="error-banner">{{ error }}</p>

    <div v-if="loading" class="panel empty-state">正在加载配置...</div>
    <template v-else>
      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Event</p>
            <h2>重建事件流</h2>
          </div>
        </div>
        <p class="panel__meta">当抓取源有更新、规则有调整，或者你想刷新首页事件流时，可以手动触发一次事件重建。</p>
        <div class="info-card__actions">
          <button
            class="button button--primary"
            type="button"
            data-testid="rebuild-events"
            :disabled="rebuilding"
            @click="handleRebuildEvents"
          >
            {{ rebuilding ? '正在重建...' : '立即重建事件' }}
          </button>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Quality</p>
            <h2>采集质量看板</h2>
          </div>
          <span class="panel__meta">最近 20 条内容的详情状态、策略分布与失败主因</span>
        </div>
        <div class="stats-grid">
          <article
            v-for="item in acquisitionStatusSummary"
            :key="item.key"
            class="metric-card"
            :data-testid="`quality-summary-${item.key}`"
          >
            <span class="metric-card__label">{{ item.label }}</span>
            <strong>{{ item.count }}</strong>
          </article>
        </div>
        <div class="summary-grid">
          <article class="summary-card" data-testid="quality-average-score">
            <h3>平均质量分</h3>
            <p>{{ acquisitionAverageScore }}</p>
          </article>
          <article class="summary-card" data-testid="quality-top-strategy">
            <h3>主力策略</h3>
            <p v-if="acquisitionTopStrategy">{{ acquisitionTopStrategy.strategy }} · {{ acquisitionTopStrategy.count }} 条</p>
            <p v-else>暂无策略记录</p>
          </article>
          <article class="summary-card" data-testid="quality-top-error">
            <h3>失败主因</h3>
            <p v-if="acquisitionTopError">{{ acquisitionTopError.errorCode }}（{{ formatQualityError(acquisitionTopError.errorCode) }}）· {{ acquisitionTopError.count }} 次</p>
            <p v-else>当前批次没有失败原因</p>
          </article>
        </div>
        <div class="summary-grid">
          <article v-if="acquisitionTrendSnapshot" class="summary-card" data-testid="quality-score-trend">
            <h3>质量分趋势</h3>
            <p>最近 {{ acquisitionTrendSnapshot.recentSize }} 条相较较早 {{ acquisitionTrendSnapshot.earlierSize || 0 }} 条：{{ formatTrendDelta(acquisitionTrendSnapshot.scoreDelta) }}</p>
          </article>
          <article v-if="acquisitionTrendSnapshot" class="summary-card" data-testid="quality-complete-trend">
            <h3>完整率趋势</h3>
            <p>最近一批完整详情占比相较上一批：{{ formatTrendDelta(acquisitionTrendSnapshot.completeDelta, '%') }}</p>
          </article>
          <article v-if="acquisitionTrendSnapshot" class="summary-card" data-testid="quality-failed-trend">
            <h3>失败率趋势</h3>
            <p>最近一批失败占比相较上一批：{{ formatTrendDelta(acquisitionTrendSnapshot.failedDelta, '%') }}</p>
          </article>
        </div>
        <div class="summary-grid">
          <article class="summary-card" data-testid="quality-error-distribution">
            <h3>失败分布 Top 3</h3>
            <ul v-if="acquisitionErrorDistribution.length > 0" class="summary-card__list">
              <li v-for="item in acquisitionErrorDistribution" :key="item.errorCode">
                <span>{{ item.errorCode }}（{{ formatQualityError(item.errorCode) }}）</span>
                <strong>{{ item.count }} 次</strong>
              </li>
            </ul>
            <p v-else>当前批次没有失败原因</p>
          </article>
          <article class="summary-card" data-testid="quality-strategy-distribution">
            <h3>策略分布 Top 3</h3>
            <ul v-if="acquisitionStrategyDistribution.length > 0" class="summary-card__list">
              <li v-for="item in acquisitionStrategyDistribution" :key="item.strategy">
                <span>{{ item.strategy }}</span>
                <strong>{{ item.count }} 条</strong>
              </li>
            </ul>
            <p v-else>暂无策略记录</p>
          </article>
          <article class="summary-card" data-testid="quality-topic-distribution">
            <h3>科技主题分布</h3>
            <ul v-if="acquisitionTopicDistribution.length > 0" class="summary-card__list">
              <li v-for="item in acquisitionTopicDistribution" :key="item.topicType">
                <span>{{ formatTechTopicType(item.topicType) }}</span>
                <strong>{{ item.count }} 条</strong>
              </li>
            </ul>
            <p v-else>当前批次还没有科技主题识别结果</p>
          </article>
        </div>
        <div class="summary-grid">
          <article class="summary-card" data-testid="quality-channel-trends">
            <h3>渠道趋势</h3>
            <ul v-if="acquisitionChannelTrends.length > 0" class="summary-card__list">
              <li v-for="item in acquisitionChannelTrends" :key="item.channelName">
                <span>{{ item.channelName }} · 质量{{ formatTrendDelta(item.scoreDelta) }} · 失败率{{ formatTrendDelta(item.failedDelta, '%') }}</span>
                <strong>{{ item.recentSize }}/{{ item.earlierSize || 0 }}</strong>
              </li>
            </ul>
            <p v-else>当前批次还没有足够的渠道趋势数据</p>
          </article>
          <article class="summary-card" data-testid="quality-keyword-distribution">
            <h3>关键词热点</h3>
            <ul v-if="acquisitionKeywordDistribution.length > 0" class="summary-card__list">
              <li v-for="item in acquisitionKeywordDistribution" :key="item.keyword">
                <span>{{ item.keyword }}</span>
                <strong>{{ item.count }} 次</strong>
              </li>
            </ul>
            <p v-else>当前批次还没有关键词识别结果</p>
          </article>
        </div>
        <div v-if="acquisitionInfos.length === 0" class="empty-state">暂时还没有可展示的采集记录。</div>
        <div v-else class="card-stack">
          <article v-for="info in acquisitionInfos" :key="info.id" class="info-card">
            <div class="info-card__top">
              <div class="tags">
                <span class="tag">{{ info.channel_name }}</span>
                <span class="tag tag--soft">{{ formatQualityStatus(info.detail_fetch_status) }}</span>
              </div>
              <span class="panel__meta">{{ info.detail_fetched_at || info.updated_at || '暂无时间' }}</span>
            </div>
            <h3>{{ info.title }}</h3>
            <div class="info-card__meta">
              <span>策略：{{ info.detail_strategy || '未记录' }}</span>
              <span>评分：{{ info.detail_score }}</span>
              <span>长度：{{ info.detail_content_length }}</span>
            </div>
            <div class="info-card__meta info-card__meta--diagnostics" data-testid="quality-tech-diagnostics">
              <span class="tag tag--soft">科技主题：{{ formatTechTopicType(info.tech_topic_type) }}</span>
              <span
                v-for="item in formatTechEntities(info.tech_entities)"
                :key="`${info.id}-entity-${item}`"
                class="tag tag--soft"
              >
                {{ item }}
              </span>
              <span
                v-for="item in formatTechKeywords(info.tech_keywords)"
                :key="`${info.id}-keyword-${item}`"
                class="tag tag--soft"
              >
                {{ item }}
              </span>
              <span
                v-if="formatTechEntities(info.tech_entities).length === 0 && formatTechKeywords(info.tech_keywords).length === 0"
                class="tag tag--soft"
              >
                暂无科技诊断
              </span>
            </div>
            <p class="info-card__summary">
              {{ info.detail_fetch_error || '当前记录没有失败原因，表示本次详情抓取已通过质量校验。' }}
            </p>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Category</p>
            <h2>新增分类</h2>
          </div>
        </div>

        <div class="settings-grid">
          <label class="field">
            <span>分类名称</span>
            <input v-model="categoryForm.name" type="text" placeholder="如：市场洞察" />
          </label>
          <label class="field">
            <span>分类编码</span>
            <input v-model="categoryForm.code" type="text" placeholder="如：market" />
          </label>
          <label class="field settings-grid__full">
            <span>分类描述</span>
            <input v-model="categoryForm.description" type="text" placeholder="用于前端展示说明" />
          </label>
        </div>

        <div class="info-card__actions">
          <button class="button button--primary" :disabled="saving" @click="handleCreateCategory">
            创建分类
          </button>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Category</p>
            <h2>分类列表</h2>
          </div>
        </div>
        <div class="card-stack">
          <article v-for="category in categories" :key="category.id" class="info-card">
            <template v-if="editingCategoryId === category.id">
              <div class="settings-grid">
                <label class="field">
                  <span>分类名称</span>
                  <input v-model="editCategoryForm.name" type="text" />
                </label>
                <label class="field">
                  <span>分类编码</span>
                  <input v-model="editCategoryForm.code" type="text" />
                </label>
                <label class="field settings-grid__full">
                  <span>分类描述</span>
                  <input v-model="editCategoryForm.description" type="text" />
                </label>
              </div>
              <div class="info-card__actions">
                <button class="button button--primary" :disabled="saving" @click="handleUpdateCategory(category.id)">
                  保存
                </button>
                <button class="button button--ghost" @click="editingCategoryId = null">取消</button>
              </div>
            </template>
            <template v-else>
              <h3>{{ category.name }}</h3>
              <p class="info-card__summary">编码：{{ category.code }}</p>
              <p class="info-card__summary">{{ category.description || '暂无描述' }}</p>
              <div class="info-card__actions">
                <button class="button button--ghost" @click="startEditCategory(category)">编辑</button>
              </div>
            </template>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Channel</p>
            <h2>新增渠道</h2>
          </div>
        </div>

        <div v-if="!hasCategoryOptions" class="empty-state">请先创建至少一个分类后再新增渠道。</div>
        <template v-else>
          <div class="settings-grid">
            <label class="field">
              <span>渠道名称</span>
              <input v-model="channelForm.name" type="text" placeholder="如：B站" />
            </label>
            <label class="field">
              <span>渠道编码</span>
              <input v-model="channelForm.code" type="text" placeholder="如：bilibili" />
            </label>
            <label class="field">
              <span>归属分类</span>
              <select v-model="channelForm.category_id">
                <option v-for="category in categories" :key="category.id" :value="category.id">
                  {{ category.name }}
                </option>
              </select>
            </label>
            <label class="field">
              <span>爬取间隔（分钟）</span>
              <input v-model.number="channelForm.crawl_interval" type="number" min="1" />
            </label>
            <label class="field settings-grid__full">
              <span>基础地址</span>
              <input v-model="channelForm.base_url" type="text" placeholder="https://example.com" />
            </label>
            <label class="field">
              <span>启用状态</span>
              <select v-model.number="channelForm.is_active">
                <option :value="1">启用</option>
                <option :value="0">停用</option>
              </select>
            </label>
          </div>

          <div class="info-card__actions">
            <button class="button button--primary" :disabled="saving" @click="handleCreateChannel">
              创建渠道
            </button>
          </div>
        </template>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Channel</p>
            <h2>渠道列表</h2>
          </div>
        </div>
        <div class="card-stack">
          <article v-for="channel in channels" :key="channel.id" class="info-card">
            <template v-if="editingChannelId === channel.id">
              <div class="settings-grid">
                <label class="field">
                  <span>渠道名称</span>
                  <input v-model="editChannelForm.name" type="text" />
                </label>
                <label class="field">
                  <span>渠道编码</span>
                  <input v-model="editChannelForm.code" type="text" />
                </label>
                <label class="field">
                  <span>归属分类</span>
                  <select v-model.number="editChannelForm.category_id">
                    <option v-for="category in categories" :key="category.id" :value="category.id">
                      {{ category.name }}
                    </option>
                  </select>
                </label>
                <label class="field">
                  <span>爬取间隔</span>
                  <input v-model.number="editChannelForm.crawl_interval" type="number" min="1" />
                </label>
                <label class="field settings-grid__full">
                  <span>基础地址</span>
                  <input v-model="editChannelForm.base_url" type="text" />
                </label>
                <label class="field">
                  <span>启用状态</span>
                  <select v-model.number="editChannelForm.is_active">
                    <option :value="1">启用</option>
                    <option :value="0">停用</option>
                  </select>
                </label>
              </div>
              <div class="info-card__actions">
                <button class="button button--primary" :disabled="saving" @click="handleUpdateChannel(channel.id)">
                  保存
                </button>
                <button class="button button--ghost" @click="editingChannelId = null">取消</button>
              </div>
            </template>
            <template v-else>
              <h3>{{ channel.name }}</h3>
              <p class="info-card__summary">编码：{{ channel.code }} · 分类：{{ channel.category_name || channel.category_id }}</p>
              <p class="info-card__summary">{{ channel.base_url }}</p>
              <div class="info-card__meta">
                <span>间隔：{{ channel.crawl_interval }} 分钟</span>
                <span>{{ channel.is_active === 1 ? '已启用' : '已停用' }}</span>
              </div>
              <div class="info-card__actions">
                <button
                  class="button button--primary"
                  type="button"
                  :data-testid="`trigger-crawl-${channel.code}`"
                  :disabled="crawlingChannelCode === channel.code"
                  @click="handleTriggerCrawl(channel.code)"
                >
                  {{ crawlingChannelCode === channel.code ? '抓取中...' : '立即抓取' }}
                </button>
                <button class="button button--ghost" @click="startEditChannel(channel)">编辑</button>
              </div>
            </template>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>
