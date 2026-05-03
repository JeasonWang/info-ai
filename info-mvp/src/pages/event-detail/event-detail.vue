<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { ref } from 'vue'
import FavoriteButton from '@/components/FavoriteButton.vue'
import { getEventById, recordReadHistory } from '@/services/api'
import { getToken } from '@/utils/storage'
import type { EventDetail } from '@/types'

const event = ref<EventDetail | null>(null)
const loading = ref(true)
const error = ref('')
const eventId = ref(0)

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
      <!-- Hero Stats Panel -->
      <view class="hero-panel">
        <view class="hero-header">
          <text class="title">{{ event.event.title }}</text>
          <FavoriteButton :event-id="eventId" />
        </view>

        <text class="summary">{{ event.event.one_line_summary }}</text>

        <view class="hero-stats">
          <view class="hero-stat">
            <text class="hero-stat-icon">&#xe7ac;</text>
            <view class="hero-stat-body">
              <text class="hero-stat-value">{{ Math.round(event.event.heat_score) }}</text>
              <text class="hero-stat-label">热度</text>
            </view>
          </view>
          <view class="hero-stat-divider" />
          <view class="hero-stat">
            <text class="hero-stat-icon">&#xe60d;</text>
            <view class="hero-stat-body">
              <text class="hero-stat-value">{{ event.source_views.length }}</text>
              <text class="hero-stat-label">来源</text>
            </view>
          </view>
          <view class="hero-stat-divider" />
          <view class="hero-stat">
            <text class="hero-stat-icon">&#xe60e;</text>
            <view class="hero-stat-body">
              <text class="hero-stat-value">{{ event.timeline.length }}</text>
              <text class="hero-stat-label">节点</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Timeline -->
      <view class="section" v-if="event.timeline.length > 0">
        <view class="section-header">
          <view class="section-dot" />
          <text class="section-title">事件时间线</text>
        </view>
        <view class="timeline">
          <view v-for="(item, idx) in event.timeline" :key="item.id" class="timeline-item">
            <view class="timeline-marker">
              <view class="timeline-dot" :class="{ 'timeline-dot--start': idx === 0, 'timeline-dot--end': idx === event.timeline.length - 1 }" />
              <view v-if="idx !== event.timeline.length - 1" class="timeline-line" />
            </view>
            <view class="timeline-content">
              <text class="timeline-time">{{ item.occurred_at }}</text>
              <text class="timeline-desc">{{ item.summary }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Multi-source Perspectives -->
      <view class="section" v-if="Object.keys(event.summaries).length > 0">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-purple);" />
          <text class="section-title">多方视角</text>
        </view>
        <view v-for="(summary, name) in event.summaries" :key="name" class="perspective-card">
          <view class="perspective-header">
            <text class="perspective-name">{{ name }}</text>
          </view>
          <text class="perspective-summary">{{ summary }}</text>
        </view>
      </view>

      <!-- Related Reports -->
      <view class="section" v-if="event.representative_sources.length > 0">
        <view class="section-header">
          <view class="section-dot" style="background: var(--cat-teal);" />
          <text class="section-title">相关报道</text>
        </view>
        <view
          v-for="source in event.representative_sources"
          :key="source.info_id"
          class="source-card"
          @click="uni.navigateTo({ url: `/pages/info-detail/info-detail?id=${source.info_id}` })"
        >
          <text class="source-card-title">{{ source.title }}</text>
          <view class="source-card-meta">
            <text class="source-card-channel">{{ source.channel_name }}</text>
            <text v-if="source.event_time" class="source-card-time">{{ source.event_time }}</text>
          </view>
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
  padding: 0 24rpx 40rpx;
}

/* Hero Panel */
.hero-panel {
  background: var(--card-bg);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  padding: 32rpx;
  margin: 0 -24rpx 24rpx;
  box-shadow: var(--shadow-sm);
}

.hero-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20rpx;
}

.title {
  flex: 1;
  font-size: var(--text-2xl);
  font-weight: 700;
  line-height: 1.4;
  color: var(--text-primary);
  margin-right: 20rpx;
}

.summary {
  display: block;
  font-size: var(--text-base);
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 28rpx;
}

.hero-stats {
  display: flex;
  align-items: center;
  background: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: 20rpx 0;
}

.hero-stat {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
}

.hero-stat-icon {
  font-family: 'uniicons';
  font-size: 36rpx;
  color: var(--brand-accent);
  opacity: 0.6;
}

.hero-stat-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.hero-stat-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.hero-stat-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.hero-stat-divider {
  width: 1rpx;
  height: 48rpx;
  background: var(--border-color);
}

/* Sections */
.section {
  margin-bottom: 32rpx;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 20rpx;
}

.section-dot {
  width: 8rpx;
  height: 32rpx;
  background: var(--brand-accent);
  border-radius: 4rpx;
}

.section-title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-primary);
}

/* Timeline */
.timeline {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 8rpx 24rpx;
  box-shadow: var(--shadow-sm);
}

.timeline-item {
  display: flex;
  gap: 16rpx;
  padding: 20rpx 0;
  position: relative;
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
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 8rpx;
}

.timeline-desc {
  display: block;
  font-size: var(--text-base);
  color: var(--text-primary);
  line-height: 1.6;
}

/* Perspective Cards */
.perspective-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 24rpx;
  margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.perspective-card:active {
  transform: translateY(-2rpx);
  box-shadow: var(--shadow-md);
}

.perspective-header {
  margin-bottom: 12rpx;
}

.perspective-name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--brand-accent);
}

.perspective-summary {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Source Cards */
.source-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 24rpx;
  margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  position: relative;
}

.source-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2rpx;
  background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.06), transparent);
  pointer-events: none;
}

.source-card:active {
  transform: translateY(-2rpx);
  box-shadow: var(--shadow-md);
}

.source-card-title {
  display: block;
  font-size: var(--text-base);
  color: var(--text-primary);
  line-height: 1.5;
  margin-bottom: 12rpx;
}

.source-card-meta {
  display: flex;
  gap: 16rpx;
}

.source-card-channel {
  font-size: var(--text-xs);
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
}

.source-card-time {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Error & Skeleton */
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
  height: 200rpx;
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
</style>
