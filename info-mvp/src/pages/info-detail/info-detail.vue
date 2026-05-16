<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { getInfoById, recordReadHistory } from '@/services/api'
import { getToken } from '@/utils/storage'
import type { InfoItem } from '@/types'

const info = ref<InfoItem | null>(null)
const loading = ref(true)
const error = ref('')
const infoId = ref(0)

onLoad((options) => {
  const id = Number(options?.id)
  if (!id) {
    uni.showToast({ title: '参数错误', icon: 'none' })
    return
  }
  infoId.value = id
  loadDetail(id)
})

async function loadDetail(id: number) {
  loading.value = true
  error.value = ''
  try {
    info.value = await getInfoById(id)
    if (getToken()) {
      recordReadHistory({ infoId: id }).catch(() => {})
    }
    uni.setNavigationBarTitle({ title: info.value?.title?.slice(0, 20) || '详情' })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function retry() {
  if (infoId.value) {
    loadDetail(infoId.value)
  }
}

function openSource() {
  if (!info.value?.source_url) return
  // #ifdef H5
  window.open(info.value.source_url, '_blank')
  // #endif
  // #ifdef MP-WEIXIN
  uni.setClipboardData({
    data: info.value.source_url,
    success: () => uni.showToast({ title: '链接已复制', icon: 'success' }),
  })
  // #endif
}

// #ifdef MP-WEIXIN
function onShareAppMessage() {
  if (!info.value) return {}
  return {
    title: info.value.title,
    path: `/pages/info-detail/info-detail?id=${infoId.value}`,
  }
}
// #endif
</script>

<template>
  <view class="detail-page">
    <view v-if="loading" class="skeleton-wrap">
      <view class="skeleton-hero" />
      <view class="skeleton-line" v-for="i in 8" :key="i" />
    </view>

    <view v-else-if="error" class="error-state">
      <text class="error-icon">&#xe60c;</text>
      <text class="error-text">{{ error }}</text>
      <text class="retry-btn" @click="retry">点击重试</text>
    </view>

    <view v-else-if="info" class="content">
      <!-- Article Header -->
      <view class="article-header">
        <view class="meta-row">
          <text class="channel-badge">{{ info.channel_name }}</text>
          <text class="time-text">{{ info.event_time || info.created_at }}</text>
        </view>
        <text class="title">{{ info.title }}</text>

        <view v-if="info.tech_keywords && info.tech_keywords.length > 0" class="tags">
          <text v-for="tag in info.tech_keywords" :key="tag" class="tag">{{ tag }}</text>
        </view>
      </view>

      <!-- Article Body -->
      <view class="article-body">
        <view v-if="info.quality_summary" class="quality-card" :class="{ 'quality-card--weak': info.needs_attention }">
          <text class="quality-title">{{ info.needs_attention ? '详情质量待补偿' : '详情质量' }}</text>
          <text class="quality-text">{{ info.quality_summary }}</text>
        </view>

        <!-- #ifdef H5 -->
        <view class="article" v-html="info.content" />
        <!-- #endif -->

        <!-- #ifdef MP-WEIXIN -->
        <rich-text class="article" :nodes="info.content" />
        <!-- #endif -->
      </view>

      <!-- Source Card -->
      <view class="source-card" @click="openSource">
        <view class="source-card-header">
          <text class="source-icon">&#xe60d;</text>
          <text class="source-label">查看原文</text>
          <text class="source-arrow">&#xe617;</text>
        </view>
        <text class="source-url">{{ info.source_url }}</text>
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
  padding: 0 0 40rpx;
}

/* Article Header */
.article-header {
  background: var(--card-bg);
  padding: 32rpx;
  margin-bottom: 16rpx;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.channel-badge {
  font-size: var(--text-xs);
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  padding: 6rpx 16rpx;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.time-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.title {
  display: block;
  font-size: var(--text-2xl);
  font-weight: 700;
  line-height: 1.4;
  color: var(--text-primary);
  margin-bottom: 20rpx;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.tag {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  background: var(--divider);
  padding: 6rpx 16rpx;
  border-radius: var(--radius-sm);
}

/* Article Body */
.article-body {
  background: var(--card-bg);
  padding: 32rpx;
  margin-bottom: 16rpx;
}

.quality-card {
  padding: 20rpx 24rpx;
  margin-bottom: 28rpx;
  border-radius: var(--radius-md);
  background: rgba(37, 99, 235, 0.08);
  border: 1rpx solid rgba(37, 99, 235, 0.12);
}

.quality-card--weak {
  background: rgba(255, 247, 237, 0.98);
  border-color: rgba(234, 88, 12, 0.16);
}

.quality-title,
.quality-text {
  display: block;
}

.quality-title {
  font-size: 26rpx;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8rpx;
}

.quality-text {
  font-size: 25rpx;
  line-height: 1.65;
  color: var(--text-secondary);
}

.article {
  font-size: var(--text-base);
  line-height: 1.8;
  color: var(--text-primary);
}

/* Source Card */
.source-card {
  background: var(--card-bg);
  margin: 0 24rpx;
  padding: 24rpx;
  border-radius: var(--radius-lg);
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

.source-card-header {
  display: flex;
  align-items: center;
  gap: 8rpx;
  margin-bottom: 12rpx;
}

.source-icon {
  font-family: 'uniicons';
  font-size: 28rpx;
  color: var(--brand-accent);
}

.source-label {
  flex: 1;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.source-arrow {
  font-family: 'uniicons';
  font-size: 24rpx;
  color: var(--text-muted);
}

.source-url {
  display: block;
  font-size: var(--text-sm);
  color: var(--brand-accent);
  word-break: break-all;
  line-height: 1.5;
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
  height: 160rpx;
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
    padding: 32px 0 72px;
  }

  .content {
    max-width: 920px;
    margin: 0 auto;
    padding: 0 28px;
  }

  .article-header,
  .article-body {
    border-radius: 16px;
    padding: 32px;
  }

  .source-card {
    margin: 0;
    border-radius: 16px;
  }

  .title {
    font-size: 32px;
    line-height: 1.35;
  }

  .article {
    font-size: 17px;
    line-height: 1.95;
  }
}
/* #endif */
</style>
