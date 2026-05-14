<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { EventListItem } from '@/types'

const props = defineProps<{
  events: EventListItem[]
  loading: boolean
  hasMore: boolean
}>()

const emit = defineEmits<{
  (e: 'load-more'): void
  (e: 'retry'): void
}>()
const loadMoreTrigger = ref<HTMLElement | null>(null)

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

function formatEventTime(value: string | null): string {
  if (!value) return ''
  const normalized = value.replace(' ', 'T')
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) {
    return value.slice(0, 16)
  }
  const now = new Date()
  const sameYear = date.getFullYear() === now.getFullYear()
  const sameDay = sameYear && date.getMonth() === now.getMonth() && date.getDate() === now.getDate()
  const pad = (num: number) => String(num).padStart(2, '0')
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  if (sameDay) return `今天 ${time}`
  if (sameYear) return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${time}`
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function qualityText(item: EventListItem): string {
  const score = item.display_quality_score ?? 0
  const level = item.display_quality_level || ''
  if (level === 'excellent') return `高可信 ${score}`
  if (level === 'good') return `可信 ${score}`
  if (level === 'weak') return `观察 ${score}`
  if (score > 0) return `质量 ${score}`
  return ''
}

function confidenceLabel(item: EventListItem): string {
  const score = item.display_quality_score ?? item.composite_score ?? 0
  if (item.status === 'monitoring' || item.display_quality_level === 'weak') return `待核实 ${Math.round(score)}`
  if (score >= 80) return `高可信 ${Math.round(score)}`
  if (score >= 60) return `可信 ${Math.round(score)}`
  if (score > 0) return `需观察 ${Math.round(score)}`
  return '需观察'
}

function qualityClass(item: EventListItem): string {
  const level = item.display_quality_level || ''
  if (level === 'excellent' || level === 'good') return 'quality-chip--good'
  if (level === 'weak') return 'quality-chip--watch'
  return 'quality-chip--muted'
}

function insightLabel(item: EventListItem): string {
  if (item.status === 'monitoring' || item.display_quality_level === 'weak') return '待核实'
  if ((item.source_count || 0) >= 3) return '多源确认'
  if ((item.display_quality_score || 0) >= 70) return '优先看'
  return '线索'
}

function reasonText(item: EventListItem): string {
  const labels: Record<string, string> = {
    empty_sources: '暂缺可核验来源',
    single_weak_source: '当前只有单一弱来源，建议观察',
    low_value_content: '正文信息量偏低',
    social_signal_without_fact_source: '已有热度，等待媒体/官方事实源确认',
    missing_complete_source: '来源信息不完整，结论需谨慎',
    missing_usable_source: '缺少可用事实来源',
    mixed_unrelated_sources: '来源疑似串台，等待重新拆分核验',
  }
  const rawReasons = String(item.display_quality_reason || '')
    .split(',')
    .map((reason) => reason.trim())
    .filter(Boolean)
  const mapped = rawReasons.map((reason) => labels[reason] || reason)
  if (mapped.length) return mapped.join(' / ')
  if (item.status === 'monitoring') return '等待更多事实源补充'
  return ''
}

function latestSignal(item: EventListItem): string {
  if (item.new_update_count > 0) return `新增 ${item.new_update_count} 条变化`
  const time = formatEventTime(item.last_updated_at)
  return time ? `最近更新 ${time}` : '等待下一轮更新'
}

// #ifdef H5
let loadObserver: IntersectionObserver | null = null

function observeLoadTrigger() {
  if (loadObserver && loadMoreTrigger.value) {
    loadObserver.observe(loadMoreTrigger.value)
  }
}

onMounted(() => {
  loadObserver = new IntersectionObserver(
    (entries) => {
      const isVisible = entries.some((entry) => entry.isIntersecting)
      if (isVisible && props.hasMore && !props.loading && props.events.length > 0) {
        emit('load-more')
      }
    },
    { root: null, rootMargin: '240px 0px', threshold: 0 },
  )
  if (loadMoreTrigger.value) {
    observeLoadTrigger()
  }
})

watch(loadMoreTrigger, () => {
  observeLoadTrigger()
})

onUnmounted(() => {
  loadObserver?.disconnect()
  loadObserver = null
})
// #endif
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
            <text class="insight-label">{{ insightLabel(item) }}</text>
            <text class="title">{{ item.title }}</text>
            <view v-if="item.new_update_count > 0" class="update-dot-wrap">
              <text class="update-badge">+{{ item.new_update_count }}</text>
              <view class="pulse-ring" />
            </view>
          </view>
        </view>

        <text class="summary">{{ item.one_line_summary }}</text>

        <view class="intel-row">
          <text class="intel-chip" :class="qualityClass(item)">{{ confidenceLabel(item) }}</text>
          <text class="intel-text">{{ latestSignal(item) }}</text>
          <text class="intel-text">{{ item.source_count }} 个来源</text>
        </view>

        <view v-if="reasonText(item)" class="reason-line">
          <text>{{ item.status === 'monitoring' ? '观察原因' : '判断依据' }}：{{ reasonText(item) }}</text>
        </view>

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
            <text v-if="item.last_updated_at" class="event-time">
              {{ formatEventTime(item.last_updated_at) }}
            </text>
            <text v-if="qualityText(item)" class="quality-chip" :class="qualityClass(item)">
              {{ qualityText(item) }}
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
      ref="loadMoreTrigger"
      class="load-more load-more-action"
      @click.stop="emit('load-more')"
    >
      <text>继续加载中...</text>
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
  box-sizing: border-box;
}

.card {
  display: flex;
  background: rgba(255, 255, 255, 0.96);
  border-radius: var(--radius-lg);
  margin-bottom: 20rpx;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  position: relative;
  box-sizing: border-box;
}

.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2rpx;
  background: linear-gradient(90deg, transparent, rgba(240, 90, 61, 0.1), transparent);
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

.insight-label {
  flex-shrink: 0;
  margin-top: 4rpx;
  padding: 5rpx 10rpx;
  color: #fff;
  background: #1f2937;
  border-radius: var(--radius-sm);
  font-size: 20rpx;
  font-weight: 800;
  line-height: 1.2;
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
  margin-bottom: 16rpx;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.intel-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8rpx;
  margin-bottom: 18rpx;
}

.intel-chip,
.intel-text {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 34rpx;
  padding: 4rpx 10rpx;
  border-radius: var(--radius-sm);
  font-size: 22rpx;
  line-height: 1.25;
  box-sizing: border-box;
}

.intel-chip {
  font-weight: 800;
}

.intel-text {
  color: var(--text-muted);
  background: var(--surface-elevated);
}

.reason-line {
  margin: -8rpx 0 18rpx;
  padding: 10rpx 14rpx;
  background: rgba(246, 162, 58, 0.1);
  border-radius: var(--radius-sm);
}

.reason-line text {
  display: block;
  color: var(--cat-orange);
  font-size: 22rpx;
  line-height: 1.45;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
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
  min-width: 0;
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

.event-time {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.4;
}

.quality-chip {
  font-size: var(--text-xs);
  padding: 4rpx 10rpx;
  border-radius: var(--radius-sm);
  line-height: 1.4;
}

.quality-chip--good {
  color: #117a4f;
  background: rgba(17, 122, 79, 0.1);
}

.quality-chip--watch {
  color: var(--cat-orange);
  background: rgba(246, 162, 58, 0.14);
}

.quality-chip--muted {
  color: var(--text-muted);
  background: var(--divider);
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
  background: linear-gradient(135deg, rgba(246, 162, 58, 0.14), rgba(240, 79, 58, 0.14));
  box-shadow: 0 0 8rpx rgba(240, 79, 58, 0.08);
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

@media (max-width: 700px) {
  .event-list {
    width: 358px;
    max-width: calc(100% - 32px);
    padding: 0;
    margin: 0 16px;
    box-sizing: border-box;
  }

  .card {
    width: 100%;
  }
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

  .insight-label {
    margin-top: 3px;
    padding: 3px 6px;
    font-size: 11px;
  }

  .summary {
    font-size: 14px;
    margin-bottom: 12px;
  }

  .intel-row {
    gap: 6px;
    margin-bottom: 12px;
  }

  .intel-chip,
  .intel-text {
    min-height: 24px;
    padding: 3px 7px;
    font-size: 12px;
  }

  .reason-line {
    margin: -6px 0 12px;
    padding: 7px 9px;
  }

  .reason-line text {
    font-size: 12px;
  }

  .badge,
  .badge-more,
  .event-time,
  .source-count {
    font-size: 12px;
  }
}
/* #endif */
</style>
