<script setup lang="ts">
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { getReadHistory } from '@/services/api'
import { getToken } from '@/utils/storage'
import type { ReadHistoryItem } from '@/types'
import { formatDateTime } from '@/utils/format'

const history = ref<ReadHistoryItem[]>([])
const loading = ref(false)
const error = ref('')

onLoad(() => {
  if (!getToken()) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    setTimeout(() => {
      uni.reLaunch({ url: '/pages/login/login' })
    }, 800)
  }
})

onShow(() => {
  if (getToken()) {
    loadHistory()
  }
})

async function loadHistory() {
  loading.value = true
  error.value = ''
  try {
    history.value = await getReadHistory()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function goDetail(item: ReadHistoryItem) {
  if (item.item_type === 'event' && item.event_id) {
    uni.navigateTo({ url: `/pages/event-detail/event-detail?id=${item.event_id}` })
  } else if (item.info_id) {
    uni.navigateTo({ url: `/pages/info-detail/info-detail?id=${item.info_id}` })
  }
}

function retry() {
  loadHistory()
}
</script>

<template>
  <view class="history-page">
    <view v-if="loading && history.length === 0" class="skeleton-list">
      <view v-for="i in 5" :key="i" class="skeleton-item">
        <view class="skeleton-header">
          <view class="skeleton-type" />
          <view class="skeleton-time" />
        </view>
        <view class="skeleton-title" />
        <view class="skeleton-subtitle" />
      </view>
    </view>

    <view v-else-if="error && history.length === 0" class="error-state">
      <text class="error-icon">&#xe60c;</text>
      <text class="error-text">{{ error }}</text>
      <text class="retry-btn" @click="retry">点击重试</text>
    </view>

    <view v-else-if="history.length === 0" class="empty">
      <text class="empty-icon">&#xe60e;</text>
      <text class="empty-text">暂无阅读记录</text>
      <text class="empty-hint">浏览事件和资讯后自动记录</text>
    </view>

    <view v-else class="list">
      <view
        v-for="item in history"
        :key="item.read_at + item.title"
        class="item"
        @click="goDetail(item)"
      >
        <view class="item-header">
          <text class="type">{{ item.item_type === 'event' ? '事件' : '资讯' }}</text>
          <text class="time">{{ formatDateTime(item.read_at) }}</text>
        </view>
        <text class="title">{{ item.title }}</text>
        <text class="subtitle">{{ item.subtitle }}</text>
        <text class="source">{{ item.source_label }}</text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.history-page {
  padding: 24rpx;
  min-height: 100vh;
  background: var(--bg-color);
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 160rpx 40rpx;
}

.empty-icon {
  font-family: 'uniicons';
  font-size: 80rpx;
  color: var(--border-color);
  margin-bottom: 24rpx;
}

.empty-text {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  margin-bottom: 8rpx;
}

.empty-hint {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 160rpx 40rpx;
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

.skeleton-list {
  padding: 0 24rpx;
}

.skeleton-item {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 24rpx;
  margin-bottom: 16rpx;
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.skeleton-type {
  width: 60rpx;
  height: 32rpx;
  background: var(--divider);
  border-radius: 6rpx;
}

.skeleton-time {
  width: 160rpx;
  height: 28rpx;
  background: var(--divider);
  border-radius: 4rpx;
}

.skeleton-title {
  height: 32rpx;
  background: var(--divider);
  border-radius: 6rpx;
  margin-bottom: 12rpx;
  width: 80%;
}

.skeleton-subtitle {
  height: 28rpx;
  background: var(--divider);
  border-radius: 4rpx;
  width: 60%;
}

.item {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 28rpx;
  margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  position: relative;
}

.item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2rpx;
  background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.06), transparent);
  pointer-events: none;
}

.item:active {
  transform: translateY(-2rpx);
  box-shadow: var(--shadow-md);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.type {
  font-size: var(--text-xs);
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  padding: 4rpx 14rpx;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.time {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.title {
  display: block;
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: 10rpx;
  line-height: 1.4;
  color: var(--text-primary);
}

.subtitle {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: 10rpx;
  line-height: 1.4;
}

.source {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
