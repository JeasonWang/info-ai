<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import FavoriteButton from '@/components/FavoriteButton.vue'
import { getEventById, recordReadHistory } from '@/services/api'
import { getToken } from '@/utils/storage'
import type { EventDetail } from '@/types'

const event = ref<EventDetail | null>(null)
const loading = ref(true)
const error = ref('')
const eventId = ref(0)
const timelineExpanded = ref(false)
const sourceExpanded = ref(false)

onLoad((options) => {
  const id = Number(options?.id)
  if (!id) {
    uni.showToast({ title: '参数错误', icon: 'none' })
    return
  }
  eventId.value = id
  loadDetail(id)
})

async function loadDetail(id: number) {
  loading.value = true
  error.value = ''
  try {
    event.value = await getEventById(id)
    if (getToken()) {
      recordReadHistory({ eventId: id }).catch(() => {})
    }
    uni.setNavigationBarTitle({ title: event.value?.event.title?.slice(0, 20) || '事件详情' })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function retry() {
  if (eventId.value) {
    loadDetail(eventId.value)
  }
}

function toggleTimeline() {
  timelineExpanded.value = !timelineExpanded.value
}

function toggleSource() {
  sourceExpanded.value = !sourceExpanded.value
}

function shareEvent() {
  // #ifdef H5
  const url = `${window.location.origin}/#/pages/event-detail/event-detail?id=${eventId.value}`
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(() => {
      uni.showToast({ title: '链接已复制', icon: 'none' })
    }).catch(() => {
      uni.showToast({ title: '复制失败', icon: 'none' })
    })
  } else {
    uni.showToast({ title: '请手动复制链接', icon: 'none' })
  }
  // #endif

  // #ifndef H5
  uni.showToast({ title: '点击右上角分享', icon: 'none' })
  // #endif
}

const primarySummary = computed(() => {
  if (!event.value) return ''
  return event.value.summaries.what_happened || event.value.summaries['发生了什么'] || ''
})

const whyMatters = computed(() => {
  if (!event.value) return ''
  return event.value.summaries.why_it_matters || event.value.summaries['为什么重要'] || ''
})

const latestUpdate = computed(() => {
  if (!event.value) return ''
  return event.value.summaries.latest_update || event.value.summaries['最新进展'] || ''
})

const heatReason = computed(() => {
  if (!event.value) return ''
  return event.value.summaries.heat_reason || event.value.summaries['为什么热'] || ''
})

const riskNotice = computed(() => {
  if (!event.value) return ''
  return event.value.summaries.risk_notice || event.value.summaries['风险提示'] || ''
})

const sourceCompare = computed(() => {
  if (!event.value) return ''
  return event.value.summaries.source_compare || event.value.summaries['来源对比'] || ''
})

const analysisConfidence = computed(() => {
  if (!event.value) return ''
  return event.value.summaries.analysis_confidence || event.value.summaries['分析可信度'] || ''
})

const hasWhyMatters = computed(() => whyMatters.value.trim().length > 0)
const hasLatestUpdate = computed(() => latestUpdate.value.trim().length > 0)
const hasHeatReason = computed(() => heatReason.value.trim().length > 0)
const hasRiskNotice = computed(() => riskNotice.value.trim().length > 0)
const hasSourceCompare = computed(() => sourceCompare.value.trim().length > 0)
const hasAnalysisConfidence = computed(() => analysisConfidence.value.trim().length > 0)

const primarySource = computed(() => {
  if (!event.value) return null
  return event.value.representative_sources.find((source) => (source.content || '').trim().length >= 80) || null
})

const primarySourceContent = computed(() => {
  const content = primarySource.value?.content || ''
  if (sourceExpanded.value || content.length <= 800) return content
  return `${content.slice(0, 800).trim()}...`
})

const sourceQualityText = computed(() => {
  const source = primarySource.value
  if (!source) return ''
  const length = source.detail_content_length || source.content.length
  return `${source.channel_name} · 评分 ${source.detail_score || 0} · ${length}字`
})

const isLatestUpdateRedundant = computed(() => {
  if (!hasLatestUpdate.value || !primarySummary.value) return false
  return latestUpdate.value.includes(primarySummary.value.slice(0, 30)) || primarySummary.value.includes(latestUpdate.value.slice(0, 30))
})

function formatRelativeTime(timeStr: string | null): string {
  if (!timeStr) return ''
  const date = new Date(timeStr.replace(' ', 'T'))
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 30) return `${days}天前`
  return timeStr.split(' ')[0]
}

// #ifdef MP-WEIXIN
function onShareAppMessage() {
  if (!event.value) return {}
  return {
    title: event.value.event.title,
    path: `/pages/event-detail/event-detail?id=${eventId.value}`,
  }
}
// #endif
</script>

<template>
  <view class="detail-page">
    <view v-if="loading" class="skeleton-wrap">
      <view class="skeleton-hero" />
      <view class="skeleton-line" v-for="i in 6" :key="i" />
    </view>

    <view v-else-if="error" class="error-state">
      <text class="error-icon">&#xe60c;</text>
      <text class="error-text">{{ error }}</text>
      <text class="retry-btn" @click="retry">点击重试</text>
    </view>

    <view v-else-if="event" class="content">
      <!-- ========== 事件头部 ========== -->
      <view class="hero-panel">
        <view class="hero-meta">
          <view class="category-tag" :style="{ background: 'var(--cat-blue)' }">
            <text>{{ event.event.primary_category.name }}</text>
          </view>
          <text class="update-time">{{ formatRelativeTime(event.event.last_updated_at) }}更新</text>
        </view>

        <text class="hero-title">{{ event.event.title }}</text>

        <text class="hero-summary">{{ event.event.one_line_summary }}</text>

        <view class="hero-actions">
          <view class="action-btn" @click="shareEvent">
            <text class="action-icon">&#xe60d;</text>
            <text class="action-label">分享</text>
          </view>
          <FavoriteButton :event-id="eventId" />
        </view>

        <view class="hero-stats">
          <view class="stat-item">
            <text class="stat-value">{{ Math.round(event.event.heat_score || 0) }}</text>
            <text class="stat-label">热度</text>
          </view>
          <view class="stat-divider" />
          <view class="stat-item">
            <text class="stat-value">{{ event.event.source_count || 0 }}</text>
            <text class="stat-label">来源</text>
          </view>
        </view>
      </view>

      <!-- ========== 发生了什么 ========== -->
      <view v-if="primarySummary" class="section">
        <view class="section-header">
          <view class="section-dot" />
          <text class="section-title">发生了什么</text>
        </view>
        <view class="fact-card">
          <text class="fact-text">{{ primarySummary }}</text>
        </view>
      </view>

      <!-- ========== 为什么重要 ========== -->
      <view v-if="hasWhyMatters" class="section">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-purple);" />
          <text class="section-title">为什么重要</text>
        </view>
        <view class="fact-card">
          <text class="fact-text">{{ whyMatters }}</text>
        </view>
      </view>

      <!-- ========== 为什么热 ========== -->
      <view v-if="hasHeatReason" class="section">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-rose);" />
          <text class="section-title">为什么热</text>
        </view>
        <view class="fact-card">
          <text class="fact-text">{{ heatReason }}</text>
        </view>
      </view>

      <!-- ========== 最新进展 ========== -->
      <view v-if="hasLatestUpdate && !isLatestUpdateRedundant" class="section">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-teal);" />
          <text class="section-title">最新进展</text>
        </view>
        <view class="fact-card">
          <text class="fact-text">{{ latestUpdate }}</text>
        </view>
      </view>

      <!-- ========== 风险提示 ========== -->
      <view v-if="hasRiskNotice" class="section">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-orange);" />
          <text class="section-title">风险提示</text>
        </view>
        <view class="fact-card fact-card--warning">
          <text class="fact-text">{{ riskNotice }}</text>
        </view>
      </view>

      <!-- ========== 分析可信度 ========== -->
      <view v-if="hasAnalysisConfidence" class="section">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-purple);" />
          <text class="section-title">分析可信度</text>
        </view>
        <view class="fact-card">
          <text class="fact-text">{{ analysisConfidence }}</text>
        </view>
      </view>

      <!-- ========== 代表原文 ========== -->
      <view v-if="primarySource" class="section">
        <view class="section-header section-header--clickable" @click="toggleSource">
          <view class="section-header-left">
            <view class="section-dot" style="background: var(--cat-orange);" />
            <text class="section-title">代表原文</text>
          </view>
          <text class="source-quality">{{ sourceQualityText }}</text>
        </view>
        <view class="article-source-card" @click="toggleSource">
          <text class="article-source-title">{{ primarySource.title }}</text>
          <text class="article-source-content">{{ primarySourceContent }}</text>
          <text v-if="primarySource.content.length > 800" class="article-source-toggle">
            {{ sourceExpanded ? '收起正文' : '展开完整正文' }}
          </text>
        </view>
      </view>

      <!-- ========== 多源视角 ========== -->
      <view v-if="event.source_views.length > 0" class="section">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-blue);" />
          <text class="section-title">多源视角</text>
        </view>
        <view v-if="hasSourceCompare" class="fact-card source-compare-card">
          <text class="fact-text">{{ sourceCompare }}</text>
        </view>
        <view class="source-view-grid">
          <view v-for="view in event.source_views" :key="view.channel_name" class="source-view-card">
            <text class="source-view-channel">{{ view.channel_name }}</text>
            <text class="source-view-summary">{{ view.summary }}</text>
          </view>
        </view>
      </view>

      <!-- ========== 证据链 ========== -->
      <view v-if="event.evidence_chain && (event.evidence_chain.evidence_sources.length > 0 || event.evidence_chain.weak_sources.length > 0)" class="section">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-green);" />
          <text class="section-title">证据链</text>
        </view>
        <view class="evidence-card">
          <text class="evidence-summary">
            可用来源 {{ event.evidence_chain.usable_source_count }} 条，需谨慎来源 {{ event.evidence_chain.weak_source_count }} 条
          </text>
          <view v-if="event.evidence_chain.platform_views.length > 0" class="evidence-platforms">
            <text
              v-for="platform in event.evidence_chain.platform_views.slice(0, 4)"
              :key="platform.channel_name"
              class="evidence-platform"
            >
              {{ platform.channel_name }} {{ platform.source_count }}
            </text>
          </view>
          <view
            v-for="source in event.evidence_chain.evidence_sources.slice(0, 3)"
            :key="source.info_id"
            class="evidence-source"
            @click="uni.navigateTo({ url: `/pages/info-detail/info-detail?id=${source.info_id}` })"
          >
            <text class="evidence-source-title">{{ source.title }}</text>
            <text class="evidence-source-meta">{{ source.channel_name }} · 质量 {{ source.detail_score }} · {{ source.quality_level }}</text>
          </view>
          <view v-if="event.evidence_chain.weak_sources.length > 0" class="evidence-warning">
            <text>风险来源：{{ event.evidence_chain.weak_sources[0].quality_summary }}</text>
          </view>
        </view>
      </view>

      <!-- ========== 关键标签 ========== -->
      <view
        v-if="event.tech_context && (event.tech_context.topics.length > 0 || event.tech_context.entities.length > 0 || event.tech_context.keywords.length > 0)"
        class="section"
      >
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-orange);" />
          <text class="section-title">关键标签</text>
        </view>
        <view class="tag-card">
          <view v-if="event.tech_context.topics.length > 0" class="tag-group">
            <text class="tag-group-label">主题</text>
            <view class="tag-list">
              <view v-for="t in event.tech_context.topics" :key="t.topic_type" class="tag-pill tag-pill--topic">
                <text>{{ t.topic_type }}</text>
              </view>
            </view>
          </view>
          <view v-if="event.tech_context.entities.length > 0" class="tag-group">
            <text class="tag-group-label">实体</text>
            <view class="tag-list">
              <view v-for="e in event.tech_context.entities" :key="e" class="tag-pill tag-pill--entity">
                <text>{{ e }}</text>
              </view>
            </view>
          </view>
          <view v-if="event.tech_context.keywords.length > 0" class="tag-group">
            <text class="tag-group-label">关键词</text>
            <view class="tag-list">
              <view v-for="k in event.tech_context.keywords" :key="k" class="tag-pill tag-pill--keyword">
                <text>{{ k }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- ========== 发展脉络（默认折叠） ========== -->
      <view v-if="event.timeline.length > 0" class="section">
        <view class="section-header section-header--clickable" @click="toggleTimeline">
          <view class="section-header-left">
            <view class="section-dot" style="background: var(--cat-rose);" />
            <text class="section-title">发展脉络</text>
          </view>
          <text class="expand-icon">{{ timelineExpanded ? '&#xe60b;' : '&#xe60a;' }}</text>
        </view>
        <view v-if="timelineExpanded" class="timeline-card">
          <view
            v-for="(item, idx) in event.timeline"
            :key="item.id"
            class="timeline-item"
          >
            <view class="timeline-marker">
              <view
                class="timeline-dot"
                :class="{ 'timeline-dot--start': idx === 0, 'timeline-dot--end': idx === event.timeline.length - 1 }"
              />
              <view v-if="idx !== event.timeline.length - 1" class="timeline-line" />
            </view>
            <view class="timeline-content">
              <text class="timeline-time">{{ item.occurred_at }}</text>
              <text class="timeline-desc">{{ item.summary }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- ========== 相关报道 ========== -->
      <view v-if="event.representative_sources.length > 0" class="section">
        <view class="section-header">
          <view class="section-dot" style="background: var(--freshness-color);" />
          <text class="section-title">相关报道</text>
        </view>
        <view
          v-for="source in event.representative_sources.slice(0, 5)"
          :key="source.info_id"
          class="source-card"
          @click="uni.navigateTo({ url: `/pages/info-detail/info-detail?id=${source.info_id}` })"
        >
          <view class="source-channel-badge">{{ source.channel_name }}</view>
          <text class="source-title">{{ source.title }}</text>
          <text v-if="source.event_time" class="source-time">{{ source.event_time }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.detail-page {
  background: var(--bg-color);
  min-height: 100vh;
}

.content {
  padding: 0 24rpx 48rpx;
}

/* ========== Hero Panel ========== */
.hero-panel {
  background: var(--card-bg);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  padding: 32rpx;
  margin: 0 -24rpx 32rpx;
  box-shadow: var(--shadow-sm);
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.category-tag {
  padding: 6rpx 16rpx;
  border-radius: var(--radius-sm);
}

.category-tag text {
  font-size: 22rpx;
  color: #fff;
  font-weight: 500;
}

.update-time {
  font-size: 22rpx;
  color: var(--text-muted);
}

.hero-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  line-height: 1.4;
  color: var(--text-primary);
  margin-bottom: 16rpx;
}

.hero-summary {
  display: block;
  font-size: 28rpx;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 24rpx;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 28rpx;
  background: var(--bg-color);
  border-radius: var(--radius-pill);
  transition: background var(--transition-fast);
}

.action-btn:active {
  background: var(--divider);
}

.action-icon {
  font-family: 'uniicons';
  font-size: 28rpx;
  color: var(--text-secondary);
}

.action-label {
  font-size: 26rpx;
  color: var(--text-secondary);
}

.hero-stats {
  display: flex;
  align-items: center;
  background: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: 20rpx 0;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
}

.stat-value {
  font-size: 36rpx;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 22rpx;
  color: var(--text-muted);
}

.stat-divider {
  width: 1rpx;
  height: 48rpx;
  background: var(--border-color);
}

/* ========== Sections ========== */
.section {
  margin-bottom: 32rpx;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 16rpx;
}

.section-header--clickable {
  justify-content: space-between;
  padding: 8rpx 0;
}

.section-header-left {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.section-dot {
  width: 8rpx;
  height: 32rpx;
  background: var(--brand-accent);
  border-radius: 4rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text-primary);
}

.expand-icon {
  font-family: 'uniicons';
  font-size: 28rpx;
  color: var(--text-muted);
  transition: transform var(--transition-fast);
}

/* ========== Fact Cards ========== */
.fact-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 28rpx;
  box-shadow: var(--shadow-sm);
}

.fact-card--warning {
  background: rgba(255, 247, 237, 0.96);
  border: 1rpx solid rgba(234, 88, 12, 0.16);
}

.fact-text {
  display: block;
  font-size: 28rpx;
  color: var(--text-primary);
  line-height: 1.8;
}

/* ========== Tag Card ========== */
.tag-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 28rpx;
  box-shadow: var(--shadow-sm);
}

.tag-group {
  margin-bottom: 20rpx;
}

.tag-group:last-child {
  margin-bottom: 0;
}

.tag-group-label {
  display: block;
  font-size: 24rpx;
  color: var(--text-muted);
  margin-bottom: 12rpx;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.tag-pill {
  display: inline-flex;
  padding: 10rpx 22rpx;
  border-radius: var(--radius-pill);
  font-size: 26rpx;
}

.tag-pill--topic {
  background: rgba(37, 99, 235, 0.08);
  color: var(--brand-accent);
}

.tag-pill--entity {
  background: rgba(124, 58, 237, 0.08);
  color: var(--cat-purple);
}

.tag-pill--keyword {
  background: rgba(234, 88, 12, 0.08);
  color: var(--cat-orange);
}

.source-quality {
  font-size: 22rpx;
  color: var(--text-muted);
  margin-left: auto;
}

.article-source-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 28rpx;
  box-shadow: var(--shadow-sm);
}

.article-source-title,
.article-source-content,
.article-source-toggle {
  display: block;
}

.article-source-title {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.5;
  margin-bottom: 16rpx;
}

.article-source-content {
  font-size: 27rpx;
  color: var(--text-primary);
  line-height: 1.85;
  white-space: pre-wrap;
}

.article-source-toggle {
  margin-top: 18rpx;
  color: var(--brand-accent);
  font-size: 26rpx;
  font-weight: 600;
}

.source-view-grid {
  display: grid;
  gap: 16rpx;
}

.source-compare-card {
  margin-bottom: 16rpx;
}

.source-view-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 24rpx;
  box-shadow: var(--shadow-sm);
}

.source-view-channel,
.source-view-summary {
  display: block;
}

.source-view-channel {
  color: var(--brand-accent);
  font-size: 24rpx;
  font-weight: 700;
  margin-bottom: 10rpx;
}

.source-view-summary {
  color: var(--text-secondary);
  font-size: 27rpx;
  line-height: 1.7;
}

/* ========== Evidence Chain ========== */
.evidence-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 28rpx;
  box-shadow: var(--shadow-sm);
}

.evidence-summary,
.evidence-source-title,
.evidence-source-meta,
.evidence-warning {
  display: block;
}

.evidence-summary {
  font-size: 27rpx;
  color: var(--text-primary);
  font-weight: 700;
  margin-bottom: 16rpx;
}

.evidence-platforms {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 16rpx;
}

.evidence-platform {
  padding: 8rpx 16rpx;
  border-radius: var(--radius-pill);
  background: rgba(37, 99, 235, 0.08);
  color: var(--brand-accent);
  font-size: 23rpx;
}

.evidence-source {
  padding: 18rpx 0;
  border-top: 1rpx solid var(--divider);
}

.evidence-source-title {
  font-size: 27rpx;
  color: var(--text-primary);
  font-weight: 700;
  line-height: 1.5;
  margin-bottom: 6rpx;
}

.evidence-source-meta {
  font-size: 23rpx;
  color: var(--text-muted);
}

.evidence-warning {
  margin-top: 12rpx;
  padding: 16rpx;
  border-radius: var(--radius-md);
  background: rgba(255, 247, 237, 0.96);
  color: var(--cat-orange);
  font-size: 24rpx;
  line-height: 1.6;
}

/* ========== Timeline ========== */
.timeline-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 8rpx 24rpx;
  box-shadow: var(--shadow-sm);
}

.timeline-item {
  display: flex;
  gap: 16rpx;
  padding: 20rpx 0;
}

.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 32rpx;
  flex-shrink: 0;
  padding-top: 6rpx;
}

.timeline-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: var(--border-color);
  border: 4rpx solid var(--card-bg);
  box-shadow: 0 0 0 2rpx var(--border-color);
}

.timeline-dot--start {
  background: var(--brand-accent);
  box-shadow: 0 0 0 2rpx rgba(37, 99, 235, 0.3);
}

.timeline-dot--end {
  background: var(--freshness-color);
  box-shadow: 0 0 0 2rpx rgba(16, 185, 129, 0.3);
}

.timeline-line {
  flex: 1;
  width: 2rpx;
  background: var(--divider);
  margin-top: 8rpx;
}

.timeline-content {
  flex: 1;
  padding-bottom: 8rpx;
}

.timeline-time {
  display: block;
  font-size: 22rpx;
  color: var(--text-muted);
  margin-bottom: 8rpx;
}

.timeline-desc {
  display: block;
  font-size: 28rpx;
  color: var(--text-primary);
  line-height: 1.6;
}

/* ========== Source Cards ========== */
.source-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 24rpx;
  margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  position: relative;
}

.source-card:active {
  transform: translateY(-2rpx);
  box-shadow: var(--shadow-md);
}

.source-channel-badge {
  display: inline-block;
  font-size: 22rpx;
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  padding: 4rpx 14rpx;
  border-radius: var(--radius-sm);
  margin-bottom: 12rpx;
}

.source-title {
  display: block;
  font-size: 28rpx;
  color: var(--text-primary);
  line-height: 1.5;
  margin-bottom: 8rpx;
}

.source-time {
  display: block;
  font-size: 22rpx;
  color: var(--text-muted);
}

/* ========== Error & Skeleton ========== */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 40rpx;
}

.error-icon {
  font-family: 'uniicons';
  font-size: 80rpx;
  color: var(--border-color);
  margin-bottom: 24rpx;
}

.error-text {
  font-size: var(--text-base);
  color: var(--text-muted);
  margin-bottom: 24rpx;
}

.retry-btn {
  display: inline-block;
  font-size: var(--text-base);
  color: var(--brand-accent);
  padding: 16rpx 40rpx;
  border: 1rpx solid var(--brand-accent);
  border-radius: var(--radius-pill);
  background: var(--brand-accent-light);
}

.skeleton-wrap {
  padding: 32rpx 24rpx;
}

.skeleton-hero {
  height: 320rpx;
  background: #e5e6eb;
  border-radius: var(--radius-lg);
  margin-bottom: 32rpx;
}

.skeleton-line {
  height: 32rpx;
  background: #e5e6eb;
  border-radius: 6rpx;
  margin-bottom: 16rpx;
}

/* #ifdef H5 */
@media (min-width: 960px) {
  .detail-page {
    padding-bottom: 72px;
  }

  .content {
    max-width: 1080px;
    margin: 0 auto;
    padding: 0 28px 72px;
  }

  .hero-panel {
    margin: 24px 0 32px;
    padding: 32px;
    border-radius: 16px;
  }

  .hero-title {
    max-width: 840px;
    font-size: 34px;
  }

  .hero-summary {
    max-width: 820px;
    font-size: 17px;
  }

  .source-view-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .source-view-card,
  .fact-card,
  .tag-card,
  .timeline-card,
  .source-card {
    border-radius: 14px;
  }
}
/* #endif */
</style>
