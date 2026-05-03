<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  keyword: string
  sortMode: 'composite' | 'latest'
}>()

const emit = defineEmits<{
  (e: 'search', value: string): void
  (e: 'sort-change', mode: 'composite' | 'latest'): void
}>()

const inputValue = ref(props.keyword)
const sortExpanded = ref(false)

function onSearch() {
  emit('search', inputValue.value)
}

function onSortChange(mode: 'composite' | 'latest') {
  emit('sort-change', mode)
  sortExpanded.value = false
}

function clearInput() {
  inputValue.value = ''
  emit('search', '')
}

function toggleSort() {
  sortExpanded.value = !sortExpanded.value
}

function getSortLabel(): string {
  return props.sortMode === 'composite' ? '综合排序' : '最新发布'
}
</script>

<template>
  <view class="filter-card">
    <view class="search-row">
      <view class="search-box">
        <text class="search-icon">&#xe618;</text>
        <input
          v-model="inputValue"
          class="search-input"
          type="text"
          placeholder="搜索事件关键词..."
          confirm-type="search"
          @confirm="onSearch"
        />
        <text v-if="inputValue" class="clear-icon" @click="clearInput">&#xe60b;</text>
      </view>
      <text class="search-btn" @click="onSearch">搜索</text>
    </view>

    <!-- 排序折叠态 -->
    <view v-if="!sortExpanded" class="sort-collapsed">
      <view class="sort-trigger" @click="toggleSort">
        <text class="sort-trigger-label">{{ getSortLabel() }}</text>
        <text class="sort-trigger-icon">&#xe60a;</text>
      </view>
    </view>

    <!-- 排序展开态 -->
    <view v-else class="sort-expanded">
      <view class="sort-options">
        <view
          class="sort-option"
          :class="{ active: sortMode === 'composite' }"
          @click="onSortChange('composite')"
        >
          <text class="sort-option-icon">&#xe60d;</text>
          <text>综合排序</text>
        </view>
        <view
          class="sort-option"
          :class="{ active: sortMode === 'latest' }"
          @click="onSortChange('latest')"
        >
          <text class="sort-option-icon">&#xe60e;</text>
          <text>最新发布</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.filter-card {
  background: var(--card-bg);
  margin: 20rpx 24rpx 0;
  padding: 24rpx;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.search-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  height: 76rpx;
  background: var(--bg-color);
  border-radius: var(--radius-pill);
  padding: 0 24rpx;
  gap: 12rpx;
  transition: box-shadow var(--transition-fast);
}

.search-box:focus-within {
  box-shadow: 0 0 0 3rpx rgba(37, 99, 235, 0.12);
}

.search-icon,
.clear-icon {
  font-family: 'uniicons';
  font-size: 30rpx;
  color: var(--text-muted);
}

.search-input {
  flex: 1;
  height: 76rpx;
  font-size: 30rpx;
  color: var(--text-primary);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-btn {
  font-size: 30rpx;
  color: var(--brand-accent);
  font-weight: 500;
  padding: 0 8rpx;
}

/* 排序折叠态 */
.sort-collapsed {
  margin-top: 16rpx;
}

.sort-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 10rpx 24rpx;
  background: var(--bg-color);
  border-radius: var(--radius-pill);
  transition: background var(--transition-fast);
}

.sort-trigger:active {
  background: var(--divider);
}

.sort-trigger-label {
  font-size: 26rpx;
  color: var(--text-secondary);
}

.sort-trigger-icon {
  font-family: 'uniicons';
  font-size: 24rpx;
  color: var(--text-muted);
}

/* 排序展开态 */
.sort-expanded {
  margin-top: 16rpx;
  animation: slide-down 0.2s ease;
}

@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateY(-4rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.sort-options {
  display: flex;
  gap: 16rpx;
}

.sort-option {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 10rpx 24rpx;
  font-size: 26rpx;
  color: var(--text-muted);
  background: var(--bg-color);
  border-radius: var(--radius-pill);
  transition: all var(--transition-fast);
}

.sort-option:active {
  transform: scale(0.95);
}

.sort-option.active {
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  font-weight: 500;
}

.sort-option-icon {
  font-family: 'uniicons';
  font-size: 24rpx;
}
</style>
