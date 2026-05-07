<script setup lang="ts">
import { ref } from 'vue'
import type { EventCategory } from '@/types'

interface FilterChannel {
  code: string
  name: string
}

const props = defineProps<{
  categories: EventCategory[]
  channels: FilterChannel[]
  activeCode: string
  activeChannelCode: string
  sortMode: 'composite' | 'latest'
}>()

const emit = defineEmits<{
  (e: 'category-change', code: string): void
  (e: 'channel-change', code: string): void
  (e: 'sort-change', mode: 'composite' | 'latest'): void
}>()

const expanded = ref(false)

function onCategoryClick(code: string) {
  emit('category-change', code)
  expanded.value = false
}

function onChannelClick(code: string) {
  emit('channel-change', code)
  expanded.value = false
}

function onSortClick(mode: 'composite' | 'latest') {
  emit('sort-change', mode)
  expanded.value = false
}

function toggleExpand() {
  expanded.value = !expanded.value
}

function getActiveCategoryName(): string {
  if (props.activeCode === 'all') return '全网'
  return props.categories.find((c) => c.code === props.activeCode)?.name ?? '全网'
}

function getActiveChannelName(): string {
  if (props.activeChannelCode === 'all') return '全部渠道'
  return props.channels.find((c) => c.code === props.activeChannelCode)?.name ?? '全部渠道'
}

function getActiveSortLabel(): string {
  return props.sortMode === 'composite' ? '综合排序' : '最新发布'
}
</script>

<template>
  <view class="filter-panel">
    <!-- 折叠态 -->
    <view v-if="!expanded" class="collapsed-bar">
      <view class="active-label">
        <text>{{ getActiveCategoryName() }}</text>
        <text class="divider">·</text>
        <text>{{ getActiveChannelName() }}</text>
        <text class="divider">·</text>
        <text>{{ getActiveSortLabel() }}</text>
      </view>
      <view class="filter-btn" @click="toggleExpand">
        <text class="filter-icon">&#xe60a;</text>
        <text class="filter-label">筛选</text>
      </view>
    </view>

    <!-- 展开态 -->
    <view v-else class="expanded-card">
      <view class="card-header">
        <text class="card-title">筛选条件</text>
        <view class="close-btn" @click="toggleExpand">
          <text class="close-icon">&#xe60b;</text>
        </view>
      </view>

      <view class="section">
        <text class="section-title">分类</text>
        <view class="option-grid">
          <view
            v-for="cat in categories"
            :key="cat.code"
            class="option-pill"
            :class="{ active: activeCode === cat.code }"
            @click="onCategoryClick(cat.code)"
          >
            <text>{{ cat.name }}</text>
          </view>
        </view>
      </view>

      <view class="section">
        <text class="section-title">渠道</text>
        <view class="option-grid">
          <view
            v-for="ch in channels"
            :key="ch.code"
            class="option-pill"
            :class="{ active: activeChannelCode === ch.code }"
            @click="onChannelClick(ch.code)"
          >
            <text>{{ ch.name }}</text>
          </view>
        </view>
      </view>

      <view class="section">
        <text class="section-title">排序</text>
        <view class="option-grid">
          <view
            class="option-pill"
            :class="{ active: sortMode === 'composite' }"
            @click="onSortClick('composite')"
          >
            <text class="pill-icon">&#xe60d;</text>
            <text>综合排序</text>
          </view>
          <view
            class="option-pill"
            :class="{ active: sortMode === 'latest' }"
            @click="onSortClick('latest')"
          >
            <text class="pill-icon">&#xe60e;</text>
            <text>最新发布</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.filter-panel {
  padding: 0 24rpx;
  box-sizing: border-box;
}

/* 折叠态 */
.collapsed-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.active-label {
  display: flex;
  align-items: center;
  gap: 12rpx;
  font-size: 24rpx;
  color: var(--text-secondary);
  font-weight: 500;
  flex: 1;
  width: 0;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}

.active-label text {
  flex-shrink: 0;
}

.active-label text:not(.divider) {
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.active-label .divider {
  color: var(--text-muted);
  font-weight: 400;
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 6rpx;
  padding: 12rpx 24rpx;
  background: var(--brand-accent-light);
  border-radius: var(--radius-pill);
  transition: background var(--transition-fast);
  margin-left: auto;
  flex-shrink: 0;
}

.filter-btn:active {
  background: rgba(240, 90, 61, 0.16);
}

.filter-icon {
  font-family: 'uniicons';
  font-size: 24rpx;
  color: var(--brand-accent);
}

.filter-label {
  font-size: 26rpx;
  color: var(--brand-accent);
  font-weight: 500;
}

/* 展开态 */
.expanded-card {
  background: rgba(255, 255, 255, 0.96);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 24rpx;
  animation: card-in 0.2s ease;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(-8rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
}

.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary);
}

.close-btn {
  width: 52rpx;
  height: 52rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--brand-soft);
}

.close-btn:active {
  background: var(--divider);
}

.close-icon {
  font-family: 'uniicons';
  font-size: 28rpx;
  color: var(--text-muted);
}

.section {
  margin-bottom: 24rpx;
}

.section:last-child {
  margin-bottom: 0;
}

.section-title {
  display: block;
  font-size: 24rpx;
  color: var(--text-muted);
  margin-bottom: 16rpx;
}

.option-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.option-pill {
  display: inline-flex;
  align-items: center;
  gap: 6rpx;
  padding: 14rpx 28rpx;
  font-size: 28rpx;
  color: var(--text-secondary);
  background: #f8f3ee;
  border-radius: var(--radius-pill);
  transition: all var(--transition-fast);
}

.option-pill:active {
  transform: scale(0.95);
}

.option-pill.active {
  color: #fff;
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  font-weight: 500;
  box-shadow: 0 4rpx 12rpx rgba(240, 90, 61, 0.22);
}

.pill-icon {
  font-family: 'uniicons';
  font-size: 24rpx;
}

/* #ifdef H5 */
@media (min-width: 960px) {
  .filter-panel {
    padding: 0 24px;
  }

  .collapsed-bar {
    justify-content: space-between;
    width: 100%;
  }

  .active-label {
    font-size: 14px;
    gap: 8px;
  }

  .filter-btn {
    padding: 8px 14px;
    gap: 6px;
  }

  .filter-label {
    font-size: 14px;
  }

  .expanded-card {
    padding: 18px;
    border-radius: 14px;
  }

  .section-title {
    font-size: 13px;
    margin-bottom: 10px;
  }

  .option-grid {
    gap: 10px;
  }

  .option-pill {
    padding: 8px 14px;
    font-size: 14px;
    border-radius: 999px;
  }
}
/* #endif */

@media (max-width: 700px) {
  .filter-panel {
    width: 358px;
    max-width: 100%;
    padding: 0;
    margin: 0;
    box-sizing: border-box;
  }

  .collapsed-bar {
    width: 100%;
  }

  .active-label {
    gap: 6px;
    font-size: 13px;
  }

  .filter-btn {
    padding: 8px 16px;
  }

  .filter-label {
    font-size: 14px;
  }

  .expanded-card {
    width: 100%;
    box-sizing: border-box;
  }
}
</style>
