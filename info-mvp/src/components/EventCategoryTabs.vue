<script setup lang="ts">
import { ref } from 'vue'
import type { EventCategory } from '@/types'

const props = defineProps<{
  categories: EventCategory[]
  activeCode: string
}>()

const emit = defineEmits<{
  (e: 'change', code: string): void
}>()

const expanded = ref(false)

function onTabClick(code: string) {
  emit('change', code)
  expanded.value = false
}

function toggleExpand() {
  expanded.value = !expanded.value
}

function getActiveName(): string {
  if (props.activeCode === 'all') return '全网'
  return props.categories.find((c) => c.code === props.activeCode)?.name ?? '全网'
}
</script>

<template>
  <view class="category-tabs">
    <!-- 折叠态：只显示当前选中的分类 -->
    <view v-if="!expanded" class="collapsed-bar">
      <view class="active-pill" @click="toggleExpand">
        <text class="pill-label">{{ getActiveName() }}</text>
        <text class="pill-icon">&#xe60a;</text>
      </view>
    </view>

    <!-- 展开态：全部分类网格 -->
    <view v-else class="expanded-panel">
      <view class="panel-header">
        <text class="panel-title">选择分类</text>
        <view class="panel-close" @click="toggleExpand">
          <text class="close-icon">&#xe60b;</text>
        </view>
      </view>

      <view class="category-grid">
        <view
          class="grid-item"
          :class="{ active: activeCode === 'all' }"
          @click="onTabClick('all')"
        >
          <text>全网</text>
        </view>

        <view
          v-for="cat in categories"
          :key="cat.code"
          class="grid-item"
          :class="{ active: activeCode === cat.code }"
          @click="onTabClick(cat.code)"
        >
          <text>{{ cat.name }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.category-tabs {
  padding: 0 24rpx;
}

/* 折叠态 */
.collapsed-bar {
  display: flex;
  align-items: center;
}

.active-pill {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 24rpx;
  background: var(--brand-accent-light);
  border-radius: var(--radius-pill);
  transition: background var(--transition-fast);
}

.active-pill:active {
  background: rgba(37, 99, 235, 0.15);
}

.pill-label {
  font-size: 28rpx;
  color: var(--brand-accent);
  font-weight: 600;
}

.pill-icon {
  font-family: 'uniicons';
  font-size: 24rpx;
  color: var(--brand-accent);
}

/* 展开态面板 */
.expanded-panel {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 24rpx;
  animation: panel-in 0.2s ease;
}

@keyframes panel-in {
  from {
    opacity: 0;
    transform: translateY(-8rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.panel-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-close {
  width: 52rpx;
  height: 52rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--bg-color);
}

.panel-close:active {
  background: var(--divider);
}

.close-icon {
  font-family: 'uniicons';
  font-size: 28rpx;
  color: var(--text-muted);
}

.category-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.grid-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 14rpx 28rpx;
  font-size: 28rpx;
  color: var(--text-secondary);
  background: var(--bg-color);
  border-radius: var(--radius-pill);
  transition: all var(--transition-fast);
}

.grid-item:active {
  transform: scale(0.95);
}

.grid-item.active {
  color: #fff;
  background: var(--brand-accent);
  font-weight: 500;
  box-shadow: 0 4rpx 12rpx rgba(37, 99, 235, 0.2);
}
</style>
