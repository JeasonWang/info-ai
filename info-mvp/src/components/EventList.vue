<script setup lang="ts">
import type { EventListItem } from '@/types'

defineProps<{
  events: EventListItem[]
  loading: boolean
  hasMore: boolean
}>()

const emit = defineEmits<{
  (e: 'load-more'): void
  (e: 'retry'): void
}>()

function goDetail(item: EventListItem) {
  uni.navigateTo({ url: `/pages/event-detail/event-detail?id=${item.id}` })
}

function getCategoryColor(code: string): string {
  const colors = ['var(--cat-blue)', 'var(--cat-purple)', 'var(--cat-teal)', 'var(--cat-orange)', 'var(--cat-rose)']
  let hash = 0
  for (let i = 0; i < code.length; i++) {
    hash = code.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

function formatHeat(score: number): string {
  const rounded = Math.round(score)
  if (rounded >= 1000) return (rounded / 1000).toFixed(1) + 'k'
  return String(rounded)
}
</script>

<template>
  <view class="event-list">
    <view
      v-for="item in events"
      :key="item.id"
      class="card"
      @click="goDetail(item)"
    >
      <view
        class="category-strip"
        :style="{ backgroundColor: getCategoryColor(item.primary_category.code) }"
      />

      <view class="card-body">
        <view class="card-header">
          <view class="title-wrap">
            <text class="title">{{ item.title }}</text>
            <view v-if="item.new_update_count > 0" class="update-dot-wrap">
              <text class="update-badge">+{{ item.new_update_count }}</text>
              <view class="pulse-ring" />
            </view>
          </view>
        </view>

        <text class="summary">{{ item.one_line_summary }}</text>

        <view class="footer">
          <view class="badges">
            <text
              v-for="badge in item.source_badges.slice(0, 3)"
              :key="badge"
              class="badge"
            >
              {{ badge }}
            </text>
            <text v-if="item.source_badges.length > 3" class="badge-more">
              +{{ item.source_badges.length - 3 }}
            </text>
          </view>

          <view class="stats">
            <view class="heat-badge">
              <text class="heat-icon">&#xe7ac;</text>
              <text class="heat-value">{{ formatHeat(item.heat_score) }}</text>
            </view>
            <text class="source-count">{{ item.source_count }} 来源</text>
          </view>
        </view>
      </view>
    </view>

    <view v-if="loading && events.length > 0" class="load-more">
      <view class="spinner" />
      <text>加载中...</text>
    </view>

    <view
      v-else-if="hasMore && events.length > 0"
      class="load-more load-more-action"
      @click.stop="emit('load-more')"
    >
      <text>加载更多</text>
    </view>

    <view
      v-else-if="!hasMore && events.length > 0"
      class="no-more"
    >
      — 已经到底了 —
    </view>

    <view v-else-if="events.length === 0 && !loading" class="empty">
      <view class="empty-icon">&#xe7ac;</view>
      <text class="empty-title">暂无相关事件</text>
      <text class="empty-hint">换个关键词或分类试试</text>
    </view>
  </view>
</template>

<style scoped>
.event-list {
  padding: 0 24rpx;
}

.card {
  display: flex;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  margin-bottom: 20rpx;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
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
  background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.08), transparent);
  pointer-events: none;
}

.card:active {
  transform: translateY(-2rpx);
  box-shadow: var(--shadow-md);
}

.category-strip {
  width: 6rpx;
  flex-shrink: 0;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
}

.card-body {
  flex: 1;
  padding: 28rpx;
  min-width: 0;
}

.card-header {
  margin-bottom: 12rpx;
}

.title-wrap {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
}

.title {
  flex: 1;
  font-size: var(--text-lg);
  font-weight: 600;
  line-height: 1.4;
  color: var(--text-primary);
}

.update-dot-wrap {
  position: relative;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-top: 4rpx;
}

.update-badge {
  font-size: var(--text-xs);
  color: #fff;
  background: var(--danger-color, #ff3b30);
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
  font-weight: 500;
  position: relative;
  z-index: 1;
}

.pulse-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  transform: translate(-50%, -50%);
  background: var(--danger-color, #ff3b30);
  border-radius: var(--radius-sm);
  opacity: 0.4;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.4;
  }
  70% {
    transform: translate(-50%, -50%) scale(1.6);
    opacity: 0;
  }
  100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0;
  }
}

.summary {
  display: block;
  font-size: var(--text-base);
  color: var(--text-secondary);
  margin-bottom: 20rpx;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
  align-items: center;
}

.badge {
  font-size: var(--text-xs);
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
}

.badge-more {
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--divider);
  padding: 4rpx 10rpx;
  border-radius: var(--radius-sm);
}

.stats {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-shrink: 0;
}

.heat-badge {
  display: inline-flex;
  align-items: center;
  gap: 4rpx;
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(239, 68, 68, 0.12));
  box-shadow: 0 0 8rpx rgba(239, 68, 68, 0.08);
}

.heat-icon {
  font-family: 'uniicons';
  font-size: 22rpx;
  color: var(--heat-gradient-end);
}

.heat-value {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--heat-gradient-end);
}

.source-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.load-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  padding: 40rpx 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.load-more-action {
  color: var(--brand-accent);
  font-weight: 600;
}

.load-more-action:active {
  opacity: 0.75;
}

.spinner {
  width: 28rpx;
  height: 28rpx;
  border: 3rpx solid var(--border-color);
  border-top-color: var(--brand-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.no-more {
  text-align: center;
  padding: 40rpx 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 0;
}

.empty-icon {
  font-family: 'uniicons';
  font-size: 80rpx;
  color: var(--border-color);
  margin-bottom: 24rpx;
}

.empty-title {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  margin-bottom: 8rpx;
}

.empty-hint {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

/* #ifdef H5 */
@media (min-width: 960px) {
  .event-list {
    padding: 0;
  }

  .card {
    margin-bottom: 16px;
    border-radius: 14px;
  }

  .card-body {
    padding: 20px;
  }

  .title {
    font-size: 18px;
    line-height: 1.45;
  }

  .summary {
    font-size: 14px;
    margin-bottom: 16px;
  }

  .badge,
  .badge-more,
  .source-count {
    font-size: 12px;
  }
}
/* #endif */
</style>
