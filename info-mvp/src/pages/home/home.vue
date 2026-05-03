<script setup lang="ts">
import { onLoad, onPullDownRefresh, onReachBottom, onPageScroll } from '@dcloudio/uni-app'
import { ref } from 'vue'
import EventList from '@/components/EventList.vue'
import EventCategoryTabs from '@/components/EventCategoryTabs.vue'
import FilterBar from '@/components/FilterBar.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import {
  getEventCategories,
  getEvents,
  getHomeFilterPreference,
  saveHomeFilterPreference,
} from '@/services/api'
import { useListLoad } from '@/composables/useListLoad'
import { useFilterMemory } from '@/composables/useFilterMemory'
import { useUserStore } from '@/stores/user'
import type { EventCategory, EventListItem } from '@/types'

const pageSize = 10
const { memory, save } = useFilterMemory()
const userStore = useUserStore()
const categories = ref<EventCategory[]>([])
const activeCategoryCode = ref(memory.value.categoryCode)
const keyword = ref(memory.value.keyword)
const appliedKeyword = ref(memory.value.keyword)
const sortMode = ref<'composite' | 'latest'>(memory.value.sortMode)
const showBackToTop = ref(false)

const {
  list: events,
  loading,
  hasMore,
  error,
  loadMore,
  refresh,
} = useListLoad<EventListItem>(async (page, size) => {
  const result = await getEvents({
    category_code: activeCategoryCode.value,
    keyword: appliedKeyword.value,
    sort: sortMode.value,
    page,
    page_size: size,
  })
  return { items: result.items, total: result.total }
})

async function loadCategories() {
  try {
    categories.value = await getEventCategories()
    ensureActiveCategoryExists()
  } catch {
    // 分类加载失败不影响主列表
  }
}

function ensureActiveCategoryExists() {
  const exists = categories.value.some((item) => item.code === activeCategoryCode.value)
  if (!exists) {
    activeCategoryCode.value = 'all'
  }
}

async function rememberCurrentFilter() {
  const preference = {
    categoryCode: activeCategoryCode.value,
    sortMode: sortMode.value,
    keyword: appliedKeyword.value,
  }
  save(preference)

  if (!userStore.isLoggedIn) return
  try {
    await saveHomeFilterPreference(preference)
  } catch {
    // 服务端偏好同步失败不阻塞
  }
}

async function restoreServerFilterPreference() {
  if (!userStore.isLoggedIn) return
  try {
    const preference = await getHomeFilterPreference()
    activeCategoryCode.value = preference.category_code || 'all'
    sortMode.value = preference.sort === 'latest' ? 'latest' : 'composite'
    keyword.value = preference.keyword || ''
    appliedKeyword.value = preference.keyword || ''
    ensureActiveCategoryExists()
    save({
      categoryCode: activeCategoryCode.value,
      sortMode: sortMode.value,
      keyword: appliedKeyword.value,
    })
  } catch {
    // 服务端不可用则继续本地缓存
  }
}

function onCategoryChange(code: string) {
  if (code === activeCategoryCode.value) return
  activeCategoryCode.value = code
  rememberCurrentFilter()
  refresh()
  scrollToTop()
}

function onSortChange(mode: 'composite' | 'latest') {
  if (mode === sortMode.value) return
  sortMode.value = mode
  rememberCurrentFilter()
  refresh()
  scrollToTop()
}

function onSearch(value: string) {
  keyword.value = value
  appliedKeyword.value = value.trim()
  rememberCurrentFilter()
  refresh()
  scrollToTop()
}

function scrollToTop() {
  uni.pageScrollTo({ scrollTop: 0, duration: 300 })
}

async function handleRetry() {
  await refresh()
}

async function handleLoadMoreRetry() {
  await loadMore()
}

function goLogin() {
  uni.navigateTo({ url: '/pages/login/login' })
}

function goFavorites() {
  uni.navigateTo({ url: '/pages/favorites/favorites' })
}

function goHistory() {
  uni.navigateTo({ url: '/pages/history/history' })
}

onLoad(() => {
  loadCategories()
  restoreServerFilterPreference().then(() => refresh())
})

onPullDownRefresh(async () => {
  await refresh()
  uni.stopPullDownRefresh()
})

onReachBottom(() => {
  loadMore()
})

onPageScroll((e) => {
  showBackToTop.value = e.scrollTop > 360
})

// #ifdef MP-WEIXIN
function onShareAppMessage() {
  return {
    title: 'InfoMVP - 热点事件聚合',
    path: '/pages/home/home',
  }
}

function onShareTimeline() {
  return {
    title: 'InfoMVP - 热点事件聚合',
    query: '',
  }
}
// #endif
</script>

<template>
  <view class="home-page">
    <!-- 顶部导航栏 -->
    <view class="nav-bar">
      <view class="brand">
        <text class="brand-name">热点事件</text>
        <text class="brand-tag">实时聚合</text>
      </view>
      <view class="user-actions">
        <template v-if="userStore.isLoggedIn">
          <view class="icon-btn" @click="goFavorites">
            <text class="icon">&#xe618;</text>
          </view>
          <view class="icon-btn" @click="goHistory">
            <text class="icon">&#xe60e;</text>
          </view>
          <view class="icon-btn" @click="goLogin">
            <text class="icon">&#xe619;</text>
          </view>
        </template>
        <view v-else class="login-btn" @click="goLogin">
          <text>登录</text>
        </view>
      </view>
    </view>

    <!-- 筛选与分类 -->
    <FilterBar
      :keyword="keyword"
      :sort-mode="sortMode"
      @search="onSearch"
      @sort-change="onSortChange"
    />
    <EventCategoryTabs
      :categories="categories"
      :active-code="activeCategoryCode"
      @change="onCategoryChange"
    />

    <SkeletonBlock v-if="loading && events.length === 0" />

    <view v-else-if="error && events.length === 0" class="error-state">
      <text class="error-icon">&#xe60c;</text>
      <text class="error-text">{{ error }}</text>
      <text class="retry-btn" @click="handleRetry">点击重试</text>
    </view>

    <EventList
      :events="events"
      :loading="loading"
      :has-more="hasMore"
      @load-more="loadMore"
      @retry="handleLoadMoreRetry"
    />

    <view
      v-if="showBackToTop"
      class="back-to-top"
      @click="scrollToTop"
    >
      <text class="back-to-top-icon">&#xe617;</text>
    </view>
  </view>
</template>

<style scoped>
.home-page {
  padding-bottom: 40rpx;
  background: var(--bg-color);
  min-height: 100vh;
}

/* 顶部导航栏 */
.nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx;
  background: var(--card-bg);
  border-bottom: 1rpx solid var(--divider);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.brand-name {
  font-size: 36rpx;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 2rpx;
}

.brand-tag {
  font-size: 20rpx;
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.icon-btn {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--bg-color);
  transition: background var(--transition-fast);
}

.icon-btn:active {
  background: var(--divider);
}

.icon-btn .icon {
  font-family: 'uniicons';
  font-size: 32rpx;
  color: var(--text-secondary);
}

.login-btn {
  padding: 14rpx 32rpx;
  background: var(--brand-accent);
  color: #fff;
  border-radius: var(--radius-pill);
  font-size: 28rpx;
  font-weight: 500;
  transition: transform var(--transition-fast), background var(--transition-fast);
}

.login-btn:active {
  transform: scale(0.95);
  background: rgba(37, 99, 235, 0.85);
}

/* 错误状态 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 40rpx;
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

/* 返回顶部 */
.back-to-top {
  position: fixed;
  right: 32rpx;
  bottom: 120rpx;
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  background: var(--card-bg);
  box-shadow: var(--shadow-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  transition: transform var(--transition-fast);
  animation: float-in 0.3s ease;
}

.back-to-top:active {
  transform: scale(0.92);
}

.back-to-top-icon {
  font-family: 'uniicons';
  font-size: 36rpx;
  color: var(--text-secondary);
}

@keyframes float-in {
  from {
    opacity: 0;
    transform: translateY(20rpx) scale(0.8);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
