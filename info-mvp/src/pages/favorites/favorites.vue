<script setup lang="ts">
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { getFavoriteEvents, removeFavoriteEvent } from '@/services/api'
import { getToken } from '@/utils/storage'
import type { FavoriteEventItem } from '@/types'

const favorites = ref<FavoriteEventItem[]>([])
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
    loadFavorites()
  }
})

async function loadFavorites() {
  loading.value = true
  error.value = ''
  try {
    favorites.value = await getFavoriteEvents()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function cancelFavorite(item: FavoriteEventItem) {
  uni.showModal({
    title: '确认取消收藏？',
    content: item.title,
    success: async (res) => {
      if (res.confirm) {
        try {
          await removeFavoriteEvent(item.id)
          favorites.value = favorites.value.filter((f) => f.id !== item.id)
          uni.showToast({ title: '已取消收藏', icon: 'success' })
        } catch {
          // handled by request
        }
      }
    },
  })
}

function goDetail(item: FavoriteEventItem) {
  uni.navigateTo({ url: `/pages/event-detail/event-detail?id=${item.id}` })
}

function retry() {
  loadFavorites()
}
</script>

<template>
  <view class="favorites-page">
    <view v-if="loading && favorites.length === 0" class="skeleton-list">
      <view v-for="i in 4" :key="i" class="skeleton-card">
        <view class="skeleton-title" />
        <view class="skeleton-summary" />
        <view class="skeleton-footer">
          <view class="skeleton-label" />
        </view>
      </view>
    </view>

    <view v-else-if="error && favorites.length === 0" class="error-state">
      <text class="error-icon">&#xe60c;</text>
      <text class="error-text">{{ error }}</text>
      <text class="retry-btn" @click="retry">点击重试</text>
    </view>

    <view v-else-if="favorites.length === 0" class="empty">
      <text class="empty-icon">&#xe619;</text>
      <text class="empty-text">暂无收藏</text>
      <text class="empty-hint">在事件详情页点击收藏按钮添加</text>
    </view>

    <view v-else class="list">
      <view
        v-for="item in favorites"
        :key="item.id"
        class="card"
        @click="goDetail(item)"
      >
        <view class="card-header">
          <view class="category-strip" />
          <text class="title">{{ item.title }}</text>
        </view>
        <text class="summary">{{ item.one_line_summary }}</text>
        <view class="footer">
          <text class="label">{{ item.source_label }}</text>
          <text class="time">{{ item.favorited_at }}</text>
        </view>
        <view class="actions">
          <text class="action-delete" @click.stop="cancelFavorite(item)">取消收藏</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.favorites-page {
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

.skeleton-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.skeleton-title {
  height: 36rpx;
  background: var(--divider);
  border-radius: 6rpx;
  margin-bottom: 16rpx;
  width: 70%;
}

.skeleton-summary {
  height: 28rpx;
  background: var(--divider);
  border-radius: 6rpx;
  margin-bottom: 16rpx;
  width: 100%;
}

.skeleton-footer {
  display: flex;
  justify-content: space-between;
}

.skeleton-label {
  width: 120rpx;
  height: 24rpx;
  background: var(--divider);
  border-radius: 4rpx;
}

.card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 28rpx;
  margin-bottom: 20rpx;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  position: relative;
}

.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2rpx;
  background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.06), transparent);
  pointer-events: none;
}

.card:active {
  transform: translateY(-2rpx);
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  margin-bottom: 12rpx;
}

.category-strip {
  width: 6rpx;
  height: 48rpx;
  background: var(--brand-accent);
  border-radius: 4rpx;
  flex-shrink: 0;
  margin-top: 4rpx;
}

.title {
  flex: 1;
  font-size: var(--text-lg);
  font-weight: 600;
  line-height: 1.4;
  color: var(--text-primary);
}

.summary {
  display: block;
  font-size: var(--text-base);
  color: var(--text-secondary);
  margin-bottom: 16rpx;
  line-height: 1.5;
}

.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.label {
  font-size: var(--text-xs);
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
}

.time {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.actions {
  display: flex;
  justify-content: flex-end;
  border-top: 1rpx solid var(--divider);
  padding-top: 16rpx;
}

.action-delete {
  font-size: var(--text-sm);
  color: var(--danger-color, #ef4444);
  padding: 8rpx 16rpx;
}
</style>
