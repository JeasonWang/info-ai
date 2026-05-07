<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  keyword: string
}>()

const emit = defineEmits<{
  (e: 'search', value: string): void
}>()

const inputValue = ref(props.keyword)

function onSearch() {
  emit('search', inputValue.value)
}

function clearInput() {
  inputValue.value = ''
  emit('search', '')
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
  </view>
</template>

<style scoped>
.filter-card {
  background: rgba(255, 255, 255, 0.94);
  margin: 16rpx 24rpx 0;
  padding: 24rpx;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.search-box {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  height: 76rpx;
  background: #f8f3ee;
  border-radius: var(--radius-pill);
  padding: 0 24rpx;
  gap: 12rpx;
  transition: box-shadow var(--transition-fast);
}

.search-box:focus-within {
  box-shadow: 0 0 0 3rpx rgba(240, 90, 61, 0.14);
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
  flex-shrink: 0;
  font-size: 30rpx;
  color: var(--brand-accent);
  font-weight: 500;
  padding: 0 8rpx;
}

@media (max-width: 700px) {
  .filter-card {
    width: 358px;
    max-width: calc(100% - 32px);
    margin: 12px 16px 0;
    padding: 16px;
    box-sizing: border-box;
  }

  .search-row {
    width: 100%;
    gap: 10px;
  }

  .search-box {
    min-width: 0;
  }

  .search-btn {
    width: 42px;
    padding: 0;
    text-align: right;
    font-size: 14px;
  }
}

/* #ifdef H5 */
@media (min-width: 960px) {
  .filter-card {
    margin: 18px 24px 0;
    padding: 16px;
    border-radius: 14px;
  }

  .search-row {
    gap: 12px;
  }

  .search-box {
    height: 44px;
    padding: 0 16px;
    border-radius: 999px;
  }

  .search-input {
    height: 44px;
    font-size: 15px;
  }

  .search-btn {
    font-size: 15px;
    padding: 0 8px;
  }
}
/* #endif */
</style>
