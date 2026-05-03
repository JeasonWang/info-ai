<script setup lang="ts">
import { ref } from 'vue'
import type { EventCategory } from '@/types'

const props = defineProps<{
  categories: EventCategory[]
  activeCode: string
  sortMode: 'composite' | 'latest'
}>()

const emit = defineEmits<{
  (e: 'category-change', code: string): void
  (e: 'sort-change', mode: 'composite' | 'latest'): void
}>()

const expanded = ref(false)

function onCategoryClick(code: string) {
  emit('category-change', code)
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
            class="option-pill"
            :class="{ active: activeCode === 'all' }"
            @click="onCategoryClick('all')"
          >
            <text>全网</text>
          </view>
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
}

/* 折叠态 */
.collapsed-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.active-label {
  display: flex;
  align-items: center;
  gap: 12rpx;
  font-size: 28rpx;
  color: var(--text-primary);
  font-weight: 500;
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
}

.filter-btn:active {
  background: rgba(37, 99, 235, 0.15);
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
  background: var(--card-bg);
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
  background: var(--bg-color);
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
  background: var(--bg-color);
  border-radius: var(--radius-pill);
  transition: all var(--transition-fast);
}

.option-pill:active {
  transform: scale(0.95);
}

.option-pill.active {
  color: #fff;
  background: var(--brand-accent);
  font-weight: 500;
  box-shadow: 0 4rpx 12rpx rgba(37, 99, 235, 0.2);
}

.pill-icon {
  font-family: 'uniicons';
  font-size: 24rpx;
}
</style>
