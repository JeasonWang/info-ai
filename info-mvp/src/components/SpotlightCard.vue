<script setup lang="ts">
import type { EventListItem, EventIntelligenceBrief, EventControversyBrief } from '@/types'

defineProps<{
  event: EventListItem
  brief: EventIntelligenceBrief | null
  controversy: EventControversyBrief | null
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()

function formatTime(value: string | null): string {
  if (!value) return ''
  const date = new Date(value.replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return value.slice(0, 16)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / 3600000)
  if (hours < 1) return '刚刚'
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function stageText(stage: string): string {
  const map: Record<string, string> = {
    observing: '观察中',
    spreading: '扩散中',
    multi_confirmed: '多源确认',
    ongoing: '持续发酵',
    potential_reversal: '可能反转',
    cooling: '降温中',
    single_unverified: '单源待核验',
  }
  return map[stage] || stage
}
</script>

<template>
  <view class="spotlight" @click="emit('click')">
    <view class="spotlight-strip" />
    <view class="spotlight-body">
      <view class="spotlight-header">
        <text class="spotlight-badge">焦点</text>
        <text v-if="brief?.stage" class="spotlight-stage">{{ stageText(brief.stage) }}</text>
        <text class="spotlight-time">{{ formatTime(event.last_updated_at) }}</text>
      </view>
      <text class="spotlight-title">{{ event.title }}</text>
      <view v-if="brief" class="spotlight-insight">
        <view v-if="brief.confidence_reason" class="insight-row">
          <text class="insight-label">判断</text>
          <text class="insight-text">{{ brief.confidence_reason }}</text>
        </view>
        <view v-if="brief.decision_hint" class="insight-row">
          <text class="insight-label">建议</text>
          <text class="insight-text">{{ brief.decision_hint }}</text>
        </view>
        <view v-if="controversy && controversy.level !== 'none' && controversy.summary" class="insight-row">
          <text class="insight-label">争议</text>
          <text class="insight-text controversy-text">{{ controversy.summary }}</text>
        </view>
      </view>
      <view class="spotlight-footer">
        <text class="spotlight-sources">{{ event.source_count }} 来源 · {{ event.primary_category.name }}</text>
        <text class="spotlight-score">
          <text>{{ event.composite_score }}</text>
          <text class="heat">{{ event.heat_score >= 1000 ? (event.heat_score / 1000).toFixed(1) + 'k' : event.heat_score }}</text>
        </text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.spotlight {
  margin: 16rpx 24rpx 0;
  background: var(--card-bg);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.spotlight:active {
  opacity: 0.95;
}

.spotlight-strip {
  height: 6rpx;
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
}

.spotlight-body {
  padding: 20rpx 24rpx;
}

.spotlight-header {
  display: flex;
  align-items: center;
  gap: 8rpx;
  margin-bottom: 12rpx;
}

.spotlight-badge {
  font-size: 20rpx;
  font-weight: 700;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
  background: var(--brand-primary);
  color: #fff;
}

.spotlight-stage {
  font-size: 20rpx;
  font-weight: 600;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
  background: rgba(74, 144, 217, 0.12);
  color: var(--cat-tech);
}

.spotlight-time {
  margin-left: auto;
  font-size: 22rpx;
  color: var(--text-muted);
}

.spotlight-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
  margin-bottom: 12rpx;
}

.spotlight-insight {
  background: var(--surface-elevated);
  border-radius: var(--radius-sm);
  padding: 16rpx 20rpx;
  margin-bottom: 16rpx;
}

.insight-row {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  margin-bottom: 8rpx;
}

.insight-row:last-child {
  margin-bottom: 0;
}

.insight-label {
  font-size: 20rpx;
  font-weight: 700;
  color: var(--text-muted);
  min-width: 56rpx;
  padding-top: 2rpx;
}

.insight-text {
  font-size: 24rpx;
  color: var(--text-secondary);
  line-height: 1.5;
}

.controversy-text {
  color: var(--cat-society);
}

.spotlight-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.spotlight-sources {
  font-size: 22rpx;
  color: var(--text-muted);
}

.spotlight-score {
  display: flex;
  align-items: center;
  gap: 16rpx;
  font-size: 22rpx;
  color: var(--text-muted);
}

.spotlight-score .heat {
  color: var(--brand-primary);
  font-weight: 700;
}
</style>
