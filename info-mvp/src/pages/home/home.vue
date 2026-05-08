<script setup lang="ts">
import { onLoad, onPullDownRefresh, onReachBottom, onPageScroll } from '@dcloudio/uni-app'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import EventList from '@/components/EventList.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import FilterBar from '@/components/FilterBar.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import {
  getChannels,
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
const channels = ref<{ code: string; name: string }[]>([])
const activeCategoryCode = ref(memory.value.categoryCode)
const activeChannelCode = ref(memory.value.channelCode)
const keyword = ref(memory.value.keyword)
const appliedKeyword = ref(memory.value.keyword)
const sortMode = ref<'composite' | 'latest'>(memory.value.sortMode)
const showBackToTop = ref(false)
const nearBottomDistance = 180
const activeCategoryName = computed(() => {
  if (activeCategoryCode.value === 'all') return '全网热点'
  return categories.value.find((item) => item.code === activeCategoryCode.value)?.name || '全网热点'
})
const activeChannelName = computed(() => {
  if (activeChannelCode.value === 'all') return '全部渠道'
  return channels.value.find((item) => item.code === activeChannelCode.value)?.name || '全部渠道'
})
const leadingEvents = computed(() => events.value.slice(0, 3))
const userInitial = computed(() => {
  const email = userStore.user?.email || ''
  return (email.trim()[0] || '我').toUpperCase()
})

const {
  list: events,
  total: eventTotal,
  loading,
  hasMore,
  error,
  loadMore,
  refresh,
} = useListLoad<EventListItem>(async (page, size) => {
  const result = await getEvents({
    category_code: activeCategoryCode.value,
    channel_code: activeChannelCode.value,
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

async function loadChannels() {
  try {
    const list = await getChannels()
    channels.value = [{ name: '全部渠道', code: 'all' }, ...list]
    ensureActiveChannelExists()
  } catch {
    // 渠道加载失败不影响主列表
  }
}

function ensureActiveCategoryExists() {
  const exists = categories.value.some((item) => item.code === activeCategoryCode.value)
  if (!exists) {
    activeCategoryCode.value = 'all'
  }
}

function ensureActiveChannelExists() {
  const exists = channels.value.some((item) => item.code === activeChannelCode.value)
  if (!exists) {
    activeChannelCode.value = 'all'
  }
}

async function rememberCurrentFilter() {
  const preference = {
    categoryCode: activeCategoryCode.value,
    channelCode: activeChannelCode.value,
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
    activeChannelCode.value = preference.channel_code || 'all'
    sortMode.value = preference.sort === 'latest' ? 'latest' : 'composite'
    keyword.value = preference.keyword || ''
    appliedKeyword.value = preference.keyword || ''
    ensureActiveCategoryExists()
    save({
      categoryCode: activeCategoryCode.value,
      channelCode: activeChannelCode.value,
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

function onChannelChange(code: string) {
  if (code === activeChannelCode.value) return
  activeChannelCode.value = code
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
  // #ifdef H5
  window.scrollTo({ top: 0, behavior: 'smooth' })
  getH5ScrollElements().forEach((el) => {
    el.scrollTo({ top: 0, behavior: 'smooth' })
  })
  // #endif
}

function updateBackToTop(scrollTop: number) {
  showBackToTop.value = scrollTop > 180
}

function maybeLoadMoreByScroll(scrollTop: number, viewportHeight: number, scrollHeight: number) {
  if (scrollHeight - scrollTop - viewportHeight <= nearBottomDistance) {
    void loadMore()
  }
}

// #ifdef H5
function getH5ScrollElements() {
  const selectors = [
    'html',
    'body',
    '#app',
    'uni-page',
    'uni-page-wrapper',
    'uni-page-body',
    '.uni-page-wrapper',
    '.uni-page-body',
    '.home-page',
  ]
  const elements = selectors
    .map((selector) => document.querySelector(selector))
    .filter((el): el is HTMLElement => el instanceof HTMLElement)
  const scrollingElement = document.scrollingElement
  if (scrollingElement instanceof HTMLElement) {
    elements.unshift(scrollingElement)
  }
  return [...new Set(elements)]
}

function getH5ScrollMetrics() {
  const scrollingElement = document.scrollingElement || document.documentElement
  const body = document.body
  const elementMetrics = getH5ScrollElements().map((el) => ({
    scrollTop: el.scrollTop || 0,
    viewportHeight: el.clientHeight || window.innerHeight || 0,
    scrollHeight: el.scrollHeight || 0,
  }))
  const scrollTop = Math.max(
    window.scrollY || 0,
    scrollingElement.scrollTop || 0,
    document.documentElement.scrollTop || 0,
    body?.scrollTop || 0,
    ...elementMetrics.map((item) => item.scrollTop),
  )
  const viewportHeight = Math.max(
    window.innerHeight || 0,
    scrollingElement.clientHeight || 0,
    document.documentElement.clientHeight || 0,
    ...elementMetrics.map((item) => item.viewportHeight),
  )
  const scrollHeight = Math.max(
    scrollingElement.scrollHeight || 0,
    document.documentElement.scrollHeight || 0,
    body?.scrollHeight || 0,
    ...elementMetrics.map((item) => item.scrollHeight),
  )
  return { scrollTop, viewportHeight, scrollHeight }
}
// #endif

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
  loadChannels()
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
  updateBackToTop(e.scrollTop)
})

// #ifdef H5
let nativeScrollFrame = 0
let scrollCheckTimer = 0
let scrollTargets: EventTarget[] = []

function bindH5ScrollTargets() {
  const nextTargets: EventTarget[] = [window, document, ...getH5ScrollElements()]
  nextTargets.forEach((target) => {
    if (!scrollTargets.includes(target)) {
      target.addEventListener('scroll', handleNativeScroll, { passive: true, capture: true })
    }
  })
  scrollTargets
    .filter((target) => !nextTargets.includes(target))
    .forEach((target) => {
      target.removeEventListener('scroll', handleNativeScroll, { capture: true })
    })
  scrollTargets = nextTargets
}

function syncH5ScrollState() {
  bindH5ScrollTargets()
  const { scrollTop, viewportHeight, scrollHeight } = getH5ScrollMetrics()
  updateBackToTop(scrollTop)
  maybeLoadMoreByScroll(scrollTop, viewportHeight, scrollHeight)
}

function handleNativeScroll() {
  if (nativeScrollFrame) return
  nativeScrollFrame = window.requestAnimationFrame(() => {
    nativeScrollFrame = 0
    syncH5ScrollState()
  })
}

onMounted(async () => {
  await nextTick()
  bindH5ScrollTargets()
  scrollCheckTimer = window.setInterval(syncH5ScrollState, 300)
  syncH5ScrollState()
})

onUnmounted(() => {
  scrollTargets.forEach((target) => {
    target.removeEventListener('scroll', handleNativeScroll, { capture: true })
  })
  scrollTargets = []
  if (scrollCheckTimer) {
    window.clearInterval(scrollCheckTimer)
  }
  if (nativeScrollFrame) {
    window.cancelAnimationFrame(nativeScrollFrame)
  }
})
// #endif

// #ifdef MP-WEIXIN
function onShareAppMessage() {
  return {
    title: '热点事件聚合',
    path: '/pages/home/home',
  }
}

function onShareTimeline() {
  return {
    title: '热点事件聚合',
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
        <text class="brand-name">信息达人</text>
        <text class="brand-count">{{ eventTotal }}</text>
        <text class="brand-tag">{{ activeCategoryName }} · {{ eventTotal }} 条</text>
      </view>
      <view class="user-actions">
        <template v-if="userStore.isLoggedIn">
          <view class="quick-action" @click="goFavorites">
            <text>收藏</text>
          </view>
          <view class="quick-action" @click="goHistory">
            <text>足迹</text>
          </view>
          <view class="avatar-btn" @click="goLogin">
            <text>{{ userInitial }}</text>
          </view>
        </template>
        <view v-else class="login-btn" @click="goLogin">
          <text>登录</text>
        </view>
      </view>
    </view>

    <view class="home-shell">
      <!-- 搜索框 -->
      <FilterBar
        :keyword="keyword"
        @search="onSearch"
      />

      <!-- 筛选面板（分类+渠道+排序） -->
      <view class="filter-wrap">
        <FilterPanel
          :categories="categories"
          :channels="channels"
          :active-code="activeCategoryCode"
          :active-channel-code="activeChannelCode"
          :sort-mode="sortMode"
          @category-change="onCategoryChange"
          @channel-change="onChannelChange"
          @sort-change="onSortChange"
        />
      </view>

      <view class="desktop-grid">
        <view class="feed-column">
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
        </view>

        <view class="insight-rail">
          <view class="rail-card">
            <text class="rail-title">当前视图</text>
            <text class="rail-line">{{ activeCategoryName }}</text>
            <text class="rail-line">{{ activeChannelName }}</text>
            <text class="rail-line">{{ sortMode === 'latest' ? '最新发布优先' : '综合热度优先' }}</text>
          </view>
          <view class="rail-card">
            <text class="rail-title">值得先看</text>
            <view v-if="leadingEvents.length" class="lead-list">
              <view
                v-for="item in leadingEvents"
                :key="item.id"
                class="lead-item"
                @click="uni.navigateTo({ url: `/pages/event-detail/event-detail?id=${item.id}` })"
              >
                <text class="lead-title">{{ item.title }}</text>
                <text class="lead-meta">{{ item.source_count }} 来源 · 热度 {{ Math.round(item.heat_score || 0) }}</text>
              </view>
            </view>
            <text v-else class="rail-empty">加载后展示最值得优先阅读的事件。</text>
          </view>
        </view>
      </view>
    </view>

    <view
      v-if="showBackToTop"
      class="back-to-top"
      @click="scrollToTop"
    >
      <text class="back-to-top-icon">↑</text>
    </view>
  </view>
</template>

<style scoped>
.home-page {
  width: 100vw;
  max-width: 100vw;
  box-sizing: border-box;
  padding-bottom: 40rpx;
  background:
    linear-gradient(180deg, rgba(255, 239, 219, 0.72) 0, rgba(243, 236, 225, 0) 280rpx),
    var(--bg-color);
  min-height: 100vh;
  overflow-x: hidden;
}

.home-shell {
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  box-sizing: border-box;
  overflow: hidden;
}

/* 顶部导航栏 */
.nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16rpx;
  padding: 24rpx;
  background: rgba(255, 250, 245, 0.92);
  border-bottom: 1rpx solid var(--divider);
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(18px);
  max-width: 100vw;
  box-sizing: border-box;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 0;
}

.brand-name {
  font-size: 36rpx;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 2rpx;
}

.brand-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36rpx;
  height: 32rpx;
  padding: 0 10rpx;
  color: #fff;
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  border-radius: var(--radius-pill);
  font-size: 22rpx;
  font-weight: 800;
  line-height: 32rpx;
}

.brand-tag {
  font-size: 20rpx;
  color: var(--brand-accent);
  background: var(--brand-accent-light);
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
  font-weight: 500;
  max-width: 240rpx;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 12rpx;
  flex-shrink: 0;
}

.quick-action {
  height: 64rpx;
  padding: 0 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-pill);
  background: var(--brand-soft);
  color: var(--brand-accent);
  font-size: 24rpx;
  font-weight: 700;
  transition: background var(--transition-fast);
}

.quick-action:active,
.avatar-btn:active {
  background: var(--divider);
}

.avatar-btn {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  color: #fff;
  font-size: 26rpx;
  font-weight: 800;
  box-shadow: var(--shadow-sm);
}

.login-btn {
  padding: 14rpx 32rpx;
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  color: #fff;
  border-radius: var(--radius-pill);
  font-size: 28rpx;
  font-weight: 500;
  transition: transform var(--transition-fast), background var(--transition-fast);
}

.login-btn:active {
  transform: scale(0.95);
  background: #dd482f;
}

.rail-title,
.rail-line,
.rail-empty,
.lead-title,
.lead-meta {
  display: block;
}

.filter-wrap {
  margin-top: 16rpx;
  margin-bottom: 16rpx;
}

.desktop-grid {
  display: block;
}

.feed-column {
  min-width: 0;
}

.insight-rail {
  display: none;
}

.rail-card {
  background: rgba(255, 255, 255, 0.94);
  border: 1rpx solid var(--divider);
  border-radius: var(--radius-lg);
  padding: 26rpx;
  box-shadow: var(--shadow-sm);
}

.rail-title {
  color: var(--text-primary);
  font-size: 30rpx;
  font-weight: 800;
  margin-bottom: 18rpx;
}

.rail-line {
  color: var(--text-secondary);
  font-size: 26rpx;
  padding: 12rpx 0;
  border-bottom: 1rpx solid var(--divider);
}

.rail-line:last-child {
  border-bottom: 0;
}

.lead-list {
  display: grid;
  gap: 14rpx;
}

.lead-item {
  padding: 18rpx;
  background: var(--surface-elevated);
  border-radius: var(--radius-md);
}

.lead-title {
  color: var(--text-primary);
  font-size: 26rpx;
  font-weight: 700;
  line-height: 1.45;
}

.lead-meta,
.rail-empty {
  color: var(--text-muted);
  font-size: 22rpx;
  line-height: 1.5;
  margin-top: 8rpx;
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
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
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
  color: #fff;
}

@media (max-width: 700px) {
  .home-shell {
    max-width: 390px;
    margin: 0;
  }

  .nav-bar {
    padding: 12px 16px;
  }

  .brand-tag {
    display: none;
  }

  .brand-count {
    min-width: 24px;
    height: 20px;
    padding: 0 7px;
    font-size: 12px;
    line-height: 20px;
  }

  .user-actions {
    gap: 8px;
  }

  .quick-action {
    height: 34px;
    padding: 0 10px;
    font-size: 12px;
  }

  .avatar-btn {
    width: 34px;
    height: 34px;
    font-size: 14px;
  }

  .filter-wrap {
    width: 358px;
    max-width: calc(100% - 32px);
    box-sizing: border-box;
    margin-top: 14px;
    margin-bottom: 14px;
    margin-left: 16px;
    margin-right: 16px;
  }

  .back-to-top {
    right: 20px;
    bottom: 32px;
    width: 44px;
    height: 44px;
  }

  .back-to-top-icon {
    font-size: 22px;
  }
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

/* #ifdef H5 */
@media (min-width: 960px) {
  .home-page {
    padding-bottom: 72px;
  }

  .nav-bar {
    padding: 18px 32px;
  }

  .brand-name {
    font-size: 24px;
    letter-spacing: 0;
  }

  .brand-tag {
    font-size: 13px;
    padding: 4px 10px;
  }

  .brand-count {
    min-width: 26px;
    height: 22px;
    padding: 0 8px;
    font-size: 13px;
    line-height: 22px;
  }

  .user-actions {
    gap: 10px;
  }

  .icon-btn {
    width: 36px;
    height: 36px;
  }

  .login-btn {
    padding: 9px 18px;
    font-size: 14px;
  }

  .desktop-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 320px;
    gap: 20px;
    padding: 0 24px;
    align-items: start;
  }

  .insight-rail {
    position: sticky;
    top: 86px;
    display: grid;
    gap: 16px;
  }

  .rail-card {
    padding: 18px;
    border-radius: 14px;
  }

  .rail-title {
    font-size: 18px;
    margin-bottom: 12px;
  }

  .rail-line,
  .lead-title {
    font-size: 14px;
  }

  .lead-meta,
  .rail-empty {
    font-size: 12px;
  }
}
/* #endif */
</style>
