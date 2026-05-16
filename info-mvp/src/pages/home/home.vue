<script setup lang="ts">
import { onLoad, onPullDownRefresh, onReachBottom, onPageScroll } from '@dcloudio/uni-app'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import EventList from '@/components/EventList.vue'
import SpotlightCard from '@/components/SpotlightCard.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import {
  getChannels,
  getEventCategories,
  getEventById,
  getEvents,
  getHomeFilterPreference,
  saveHomeFilterPreference,
} from '@/services/api'
import { useListLoad } from '@/composables/useListLoad'
import { useFilterMemory } from '@/composables/useFilterMemory'
import { useUserStore } from '@/stores/user'
import type { EventCategory, EventListItem, EventIntelligenceBrief, EventControversyBrief } from '@/types'

const pageSize = 10
const { memory, save } = useFilterMemory()
const userStore = useUserStore()
const categories = ref<EventCategory[]>([])
const channels = ref<{ code: string; name: string }[]>([])
const activeCategoryCode = ref(memory.value.categoryCode)
const activeChannelCode = ref(memory.value.channelCode || 'all')
const keyword = ref(memory.value.keyword)
const appliedKeyword = ref(memory.value.keyword)
const sortMode = ref<'composite' | 'latest'>(memory.value.sortMode)
const feedStatus = ref<'active' | 'monitoring'>('active')
const showBackToTop = ref(false)
const dockVisible = ref(true)
const displayMode = ref<'card' | 'compact'>('compact')
const showSearch = ref(false)
const showFilterPanel = ref(false)
const nearBottomDistance = 180

const feedOptions = [
  { value: 'active' as const, label: '可信事件', meta: '多源确认' },
  { value: 'monitoring' as const, label: '观察中', meta: '待核实' },
]

const userInitial = computed(() => {
  const email = userStore.user?.email || ''
  return (email.trim()[0] || '我').toUpperCase()
})

const activeCategoryName = computed(() => {
  if (activeCategoryCode.value === 'all') return '全部'
  return categories.value.find(c => c.code === activeCategoryCode.value)?.name || '全部'
})

const activeChannelName = computed(() => {
  if (activeChannelCode.value === 'all') return '全部渠道'
  return channels.value.find(c => c.code === activeChannelCode.value)?.name || '全部渠道'
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
    status: feedStatus.value,
    sort: sortMode.value,
    page,
    page_size: size,
  })
  return { items: result.items, total: result.total }
})

const spotlightEvent = computed(() => events.value[0] || null)
const spotlightBrief = ref<EventIntelligenceBrief | null>(null)
const spotlightControversy = ref<EventControversyBrief | null>(null)

const situationStats = computed(() => {
  const total = events.value.length
  const highAttention = events.value.filter(e => (e.composite_score || 0) > 80).length
  return { total, eventTotal: eventTotal.value, highAttention }
})

async function loadSpotlightDetail() {
  const top = events.value[0]
  if (!top) {
    spotlightBrief.value = null
    spotlightControversy.value = null
    return
  }
  try {
    const detail = await getEventById(top.id)
    spotlightBrief.value = detail.intelligence_brief || null
    spotlightControversy.value = detail.controversy_brief || null
  } catch {
    spotlightBrief.value = null
    spotlightControversy.value = null
  }
}

async function loadCategories() {
  try {
    categories.value = await getEventCategories()
    ensureActiveCategoryExists()
  } catch { /* noop */ }
}

async function loadChannels() {
  try {
    const list = await getChannels()
    channels.value = [{ name: '全部渠道', code: 'all' }, ...list]
    ensureActiveChannelExists()
  } catch { /* noop */ }
}

function ensureActiveCategoryExists() {
  const exists = categories.value.some(item => item.code === activeCategoryCode.value)
  if (!exists) activeCategoryCode.value = 'all'
}

function ensureActiveChannelExists() {
  const exists = channels.value.some(item => item.code === activeChannelCode.value)
  if (!exists) activeChannelCode.value = 'all'
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
  try { await saveHomeFilterPreference(preference) } catch { /* noop */ }
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
    ensureActiveChannelExists()
    save({
      categoryCode: activeCategoryCode.value,
      channelCode: activeChannelCode.value,
      sortMode: sortMode.value,
      keyword: appliedKeyword.value,
    })
  } catch { /* noop */ }
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

function onFeedStatusChange(status: 'active' | 'monitoring') {
  if (status === feedStatus.value) return
  feedStatus.value = status
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

function toggleDisplayMode() {
  displayMode.value = displayMode.value === 'compact' ? 'card' : 'compact'
}

function scrollToTop() {
  uni.pageScrollTo({ scrollTop: 0, duration: 300 })
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

function goSpotlightDetail() {
  if (spotlightEvent.value) {
    uni.navigateTo({ url: `/pages/event-detail/event-detail?id=${spotlightEvent.value.id}` })
  }
}

async function handleRetry() { await refresh() }
async function handleLoadMoreRetry() { await loadMore() }

function updateBackToTop(scrollTop: number) {
  showBackToTop.value = scrollTop > 300
}

let lastScrollTop = 0

function handleScroll(scrollTop: number) {
  showBackToTop.value = scrollTop > 300
  dockVisible.value = !(scrollTop > 300 && scrollTop > lastScrollTop)
  lastScrollTop = scrollTop
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

onReachBottom(() => { loadMore() })

onPageScroll((e) => {
  handleScroll(e.scrollTop)
})

onMounted(async () => {
  // #ifdef H5
  window.addEventListener('scroll', () => {
    const y = window.scrollY || document.documentElement.scrollTop || 0
    handleScroll(y)
  }, { passive: true })
  // #endif
})

watch(events, () => { loadSpotlightDetail() })
</script>

<template>
  <view class="page-root">
    <view class="home-page">
      <!-- Nav Bar -->
      <view class="nav-bar">
        <view class="nav-brand">
          <view class="nav-logo"><text class="nav-logo-text">AI</text></view>
          <text class="nav-title">AI 情报台</text>
        </view>
        <view class="nav-actions">
          <view class="nav-icon-btn" @click="showSearch = !showSearch">
            <text class="nav-icon-text">&#x1F50D;</text>
          </view>
          <view v-if="userStore.isLoggedIn" class="avatar-btn" @click="goLogin">
            <text>{{ userInitial }}</text>
          </view>
          <view v-else class="login-btn" @click="goLogin"><text>登录</text></view>
        </view>
      </view>

      <!-- Search (expandable) -->
      <view v-if="showSearch" class="search-bar">
        <input
          class="search-input"
          :value="keyword"
          placeholder="搜索事件关键词..."
          confirm-type="search"
          @confirm="onSearch(($event as any).detail?.value || '')"
        />
        <view class="search-cancel" @click="showSearch = false; keyword = ''; onSearch('')">
          <text>取消</text>
        </view>
      </view>

      <view class="home-shell">
        <!-- View Switch -->
        <view class="view-switch">
          <view
            v-for="option in feedOptions"
            :key="option.value"
            class="view-switch-item"
            :class="{ active: feedStatus === option.value }"
            @click="onFeedStatusChange(option.value)"
          >
            <text class="switch-label">{{ option.label }}</text>
            <text class="switch-meta">{{ option.meta }}</text>
          </view>
        </view>

        <!-- Situation Strip -->
        <view class="situation-strip">
          <view class="stat-card">
            <text class="stat-num">{{ situationStats.eventTotal }}</text>
            <text class="stat-label">活跃情报</text>
          </view>
          <view class="stat-card">
            <text class="stat-num accent">+{{ situationStats.total }}</text>
            <text class="stat-label">已加载</text>
          </view>
          <view class="stat-card">
            <text class="stat-num">{{ situationStats.highAttention }}</text>
            <text class="stat-label">高关注度</text>
          </view>
        </view>

        <!-- Spotlight Card -->
        <SpotlightCard
          v-if="spotlightEvent"
          :event="spotlightEvent"
          :brief="spotlightBrief"
          :controversy="spotlightControversy"
          @click="goSpotlightDetail"
        />

        <!-- Filter Bar: category tabs + filter toggle + mode toggle -->
        <view class="filter-bar">
          <scroll-view scroll-x class="filter-tabs-scroll">
            <view class="filter-tabs">
              <view class="filter-tab" :class="{ active: activeCategoryCode === 'all' }" @click="onCategoryChange('all')">
                <text>全部</text>
              </view>
              <view
                v-for="cat in categories"
                :key="cat.code"
                class="filter-tab"
                :class="{ active: activeCategoryCode === cat.code }"
                @click="onCategoryChange(cat.code)"
              >
                <text>{{ cat.name }}</text>
              </view>
            </view>
          </scroll-view>
          <view class="filter-actions">
            <view class="filter-btn" :class="{ active: showFilterPanel }" @click="showFilterPanel = !showFilterPanel">
              <text class="filter-btn-icon">&#x2699;</text>
              <view v-if="activeChannelCode !== 'all' || sortMode === 'latest'" class="filter-indicator" />
            </view>
            <view class="filter-btn" @click="toggleDisplayMode">
              <text class="filter-btn-icon">{{ displayMode === 'compact' ? '&#x2630;' : '&#x2261;' }}</text>
            </view>
          </view>
        </view>

        <!-- Expandable Filter Panel (channel + sort) -->
        <view v-if="showFilterPanel" class="filter-panel">
          <view class="filter-section">
            <text class="filter-section-title">渠道</text>
            <view class="filter-pills">
              <view
                v-for="ch in channels"
                :key="ch.code"
                class="pill"
                :class="{ active: activeChannelCode === ch.code }"
                @click="onChannelChange(ch.code)"
              >
                <text>{{ ch.name }}</text>
              </view>
            </view>
          </view>
          <view class="filter-section">
            <text class="filter-section-title">排序</text>
            <view class="filter-pills">
              <view class="pill" :class="{ active: sortMode === 'composite' }" @click="onSortChange('composite')">
                <text>综合优先</text>
              </view>
              <view class="pill" :class="{ active: sortMode === 'latest' }" @click="onSortChange('latest')">
                <text>最新优先</text>
              </view>
            </view>
          </view>
        </view>

        <!-- Active filter hint (when filters are active and panel is closed) -->
        <view v-if="!showFilterPanel && (activeChannelCode !== 'all' || sortMode === 'latest')" class="active-filters">
          <text class="active-filter-tag" v-if="activeChannelCode !== 'all'" @click="onChannelChange('all')">{{ activeChannelName }} ✕</text>
          <text class="active-filter-tag" v-if="sortMode === 'latest'" @click="onSortChange('composite')">最新优先 ✕</text>
        </view>

        <!-- Main Content -->
        <view class="feed-column">
          <SkeletonBlock v-if="loading && events.length === 0" />
          <view v-else-if="error && events.length === 0" class="error-state">
            <text class="error-text">{{ error }}</text>
            <text class="retry-btn" @click="handleRetry">重试</text>
          </view>
          <EventList
            :events="events"
            :loading="loading"
            :has-more="hasMore"
            :display-mode="displayMode"
            @load-more="loadMore"
            @retry="handleLoadMoreRetry"
          />
        </view>
      </view>
    </view>

    <!-- Back to Top -->
    <view v-if="showBackToTop" class="back-to-top" @click="scrollToTop">
      <text class="back-to-top-icon">↑</text>
    </view>

    <!-- Floating Dock -->
    <view class="dock-wrap" :style="{ opacity: dockVisible ? 1 : 0, transform: dockVisible ? 'translateY(0)' : 'translateY(100%)' }">
      <view class="dock">
        <view class="dock-item active" @click="() => {}">
          <text class="dock-icon">&#x25C9;</text>
          <text class="dock-label">情报</text>
        </view>
        <view class="dock-ai">
          <view class="dock-ai-orb"><text class="ai-icon">&#x2726;</text></view>
          <text class="dock-label ai-label">智询</text>
        </view>
        <view class="dock-item" @click="userStore.isLoggedIn ? goFavorites() : goLogin()">
          <text class="dock-icon">&#x25CE;</text>
          <text class="dock-label">我的</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page-root {
  width: 100%;
  min-height: 100vh;
  position: relative;
}

.home-page {
  width: 100%;
  box-sizing: border-box;
  padding-bottom: 180rpx;
  background: var(--bg-color);
  min-height: 100vh;
}

.home-shell {
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  box-sizing: border-box;
}

/* Nav Bar */
.nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16rpx;
  padding: 20rpx 24rpx;
  background: rgba(255, 250, 245, 0.92);
  border-bottom: 1rpx solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(18px);
  box-sizing: border-box;
}

.nav-brand { display: flex; align-items: center; gap: 12rpx; }

.nav-logo {
  width: 56rpx; height: 56rpx; border-radius: 14rpx;
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  display: flex; align-items: center; justify-content: center;
}

.nav-logo-text { color: #fff; font-size: 28rpx; font-weight: 800; }

.nav-title { font-size: 34rpx; font-weight: 700; color: var(--text-primary); }

.nav-actions { display: flex; align-items: center; gap: 12rpx; }

.nav-icon-btn {
  width: 64rpx; height: 64rpx; display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
}
.nav-icon-btn:active { background: var(--brand-accent-light); }
.nav-icon-text { font-size: 32rpx; }

.avatar-btn {
  width: 60rpx; height: 60rpx; display: flex; align-items: center; justify-content: center;
  border-radius: 50%; background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  color: #fff; font-size: 26rpx; font-weight: 800;
}

.login-btn {
  padding: 12rpx 28rpx; border-radius: var(--radius-pill);
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  color: #fff; font-size: 26rpx; font-weight: 500;
}
.login-btn:active { opacity: 0.9; }

/* Search */
.search-bar {
  display: flex; align-items: center; gap: 16rpx; padding: 12rpx 24rpx;
  background: var(--card-bg); border-bottom: 1rpx solid var(--border-color);
}

.search-input {
  flex: 1; height: 64rpx; padding: 0 20rpx;
  background: var(--surface-elevated); border-radius: var(--radius-pill);
  font-size: 26rpx; color: var(--text-primary);
}

.search-cancel { padding: 12rpx; color: var(--brand-primary); font-size: 26rpx; }

/* View Switch */
.view-switch {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8rpx; margin: 20rpx 24rpx 0; padding: 6rpx;
  background: rgba(255, 255, 255, 0.6); border-radius: var(--radius-pill);
}

.view-switch-item {
  display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 2rpx;
  padding: 14rpx 0; border-radius: var(--radius-pill);
  color: var(--text-muted); transition: all 0.25s;
}

.view-switch-item.active {
  color: #fff; background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  box-shadow: 0 4rpx 16rpx rgba(240, 90, 61, 0.3);
}

.switch-label { font-size: 26rpx; font-weight: 600; }
.switch-meta { font-size: 20rpx; opacity: 0.7; }

/* Situation Strip */
.situation-strip {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 12rpx; margin: 20rpx 24rpx 0;
}

.stat-card {
  background: var(--card-bg); border-radius: var(--radius-sm);
  padding: 20rpx; box-shadow: var(--shadow-sm); text-align: center;
}

.stat-num { font-size: 48rpx; font-weight: 800; color: var(--text-primary); line-height: 1.1; }
.stat-num.accent { color: var(--brand-primary); }
.stat-label { font-size: 22rpx; color: var(--text-muted); margin-top: 4rpx; }

/* Filter Bar */
.filter-bar {
  display: flex; align-items: center; gap: 8rpx;
  padding: 20rpx 24rpx 0; position: relative;
}

.filter-tabs-scroll { flex: 1; white-space: nowrap; }
.filter-tabs { display: flex; gap: 0; }

.filter-tab {
  flex-shrink: 0; padding: 12rpx 28rpx; font-size: 26rpx; font-weight: 500;
  color: var(--text-muted); border-bottom: 4rpx solid transparent; transition: all 0.2s;
}

.filter-tab.active {
  color: var(--brand-primary); font-weight: 700; border-bottom-color: var(--brand-primary);
}

.filter-actions { display: flex; align-items: center; gap: 8rpx; flex-shrink: 0; }

.filter-btn {
  width: 60rpx; height: 60rpx; border-radius: 14rpx;
  display: flex; align-items: center; justify-content: center;
  background: var(--card-bg); border: 1rpx solid var(--border-color);
  position: relative;
}
.filter-btn:active { background: var(--brand-accent-light); }
.filter-btn.active { background: var(--brand-accent-light); border-color: var(--brand-primary); }
.filter-btn-icon { font-size: 28rpx; }

.filter-indicator {
  position: absolute; top: -4rpx; right: -4rpx;
  width: 14rpx; height: 14rpx; border-radius: 50%;
  background: var(--brand-primary); border: 2rpx solid var(--bg-color);
}

/* Filter Panel */
.filter-panel {
  margin: 12rpx 24rpx 0; padding: 24rpx;
  background: var(--card-bg); border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.filter-section { margin-bottom: 20rpx; }
.filter-section:last-child { margin-bottom: 0; }

.filter-section-title {
  font-size: 22rpx; font-weight: 700; color: var(--text-muted);
  margin-bottom: 12rpx;
}

.filter-pills { display: flex; flex-wrap: wrap; gap: 12rpx; }

.pill {
  padding: 10rpx 24rpx; border-radius: var(--radius-pill);
  font-size: 24rpx; color: var(--text-secondary);
  background: var(--surface-elevated); border: 1rpx solid var(--border-color);
}
.pill.active {
  color: #fff; background: var(--brand-primary); border-color: var(--brand-primary);
}
.pill:active { opacity: 0.8; }

/* Active filter tags */
.active-filters {
  display: flex; gap: 12rpx; padding: 8rpx 24rpx 0; flex-wrap: wrap;
}

.active-filter-tag {
  font-size: 22rpx; color: var(--brand-primary); background: var(--brand-accent-light);
  padding: 6rpx 16rpx; border-radius: var(--radius-pill);
}

/* Feed column */
.feed-column { min-width: 0; }

/* Error */
.error-state { display: flex; flex-direction: column; align-items: center; padding: 160rpx 40rpx; }
.error-text { font-size: var(--text-base); color: var(--text-muted); margin-bottom: 24rpx; }
.retry-btn {
  font-size: var(--text-base); color: var(--brand-primary);
  padding: 16rpx 40rpx; border: 1rpx solid var(--brand-primary);
  border-radius: var(--radius-pill); background: var(--brand-accent-light);
}

/* Back to Top */
.back-to-top {
  position: fixed; right: 28rpx; bottom: 200rpx;
  width: 72rpx; height: 72rpx; border-radius: 50%;
  background: var(--card-bg); box-shadow: var(--shadow-md);
  display: flex; align-items: center; justify-content: center;
  z-index: 300;
}
.back-to-top:active { transform: scale(0.9); }
.back-to-top-icon { font-size: 32rpx; color: var(--text-secondary); }

/* Dock */
.dock-wrap {
  position: fixed; bottom: 0; left: 0; right: 0; z-index: 300;
  display: flex; justify-content: center;
  padding: 0 0 calc(16rpx + env(safe-area-inset-bottom));
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.35s;
}

.dock {
  display: flex; align-items: flex-end; width: 72%;
  background: rgba(255, 250, 245, 0.9);
  backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
  border-radius: 40rpx; padding: 10rpx 0;
  box-shadow: 0 4rpx 32rpx rgba(106, 70, 43, 0.12), 0 0 0 1rpx rgba(234, 223, 213, 0.5);
}

.dock-item {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 4rpx; padding: 14rpx 0; border-radius: 28rpx;
  position: relative;
}

.dock-icon { font-size: 40rpx; color: var(--text-muted); }
.dock-label { font-size: 18rpx; color: var(--text-muted); }

.dock-item.active .dock-icon { color: var(--brand-primary); }
.dock-item.active .dock-label { color: var(--brand-primary); font-weight: 600; }
.dock-item.active::before {
  content: ''; position: absolute; inset: 2rpx; border-radius: 26rpx;
  background: var(--brand-accent-light);
}

.dock-ai {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; margin-top: -24rpx; position: relative; z-index: 1;
}

.dock-ai-orb {
  width: 80rpx; height: 80rpx; border-radius: 50%;
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4rpx 20rpx rgba(240, 90, 61, 0.35);
}
.dock-ai-orb:active { transform: scale(0.93); }
.ai-icon { font-size: 40rpx; color: #fff; }
.ai-label { color: var(--brand-primary) !important; margin-top: 4rpx; }

@keyframes orb-glow {
  0%, 100% { box-shadow: 0 4rpx 20rpx rgba(240, 90, 61, 0.35); }
  50% { box-shadow: 0 4rpx 28rpx rgba(240, 90, 61, 0.45), 0 0 0 6rpx rgba(240, 90, 61, 0.06); }
}
.dock-ai-orb { animation: orb-glow 3s ease-in-out infinite; }

/* Responsive */
@media (max-width: 700px) {
  .home-shell { max-width: 100%; margin: 0; }
  .nav-bar { padding: 16rpx 24rpx; }

  .view-switch { width: calc(100% - 32px); margin: 16px 16px 0; padding: 3px; gap: 3px; }
  .view-switch-item { padding: 10px 0; }
  .switch-label { font-size: 13px; }
  .switch-meta { font-size: 10px; }

  .situation-strip { margin: 12px 16px 0; gap: 6px; }
  .stat-card { padding: 10px; }
  .stat-num { font-size: 24px; }
  .stat-label { font-size: 11px; }

  .filter-bar { padding: 12px 16px 0; }
  .filter-tab { padding: 6px 14px; font-size: 13px; }
  .filter-panel { margin: 10px 16px 0; padding: 14px; }
  .pill { padding: 6px 12px; font-size: 12px; }

  .back-to-top { right: 16px; bottom: 120rpx; width: 36px; height: 36px; }
  .back-to-top-icon { font-size: 16px; }
}

/* #ifdef H5 */
@media (min-width: 960px) {
  .home-page { padding-bottom: 72px; }
  .nav-bar { padding: 14px 32px; }
  .nav-title { font-size: 18px; }
  .view-switch { max-width: 760px; margin: 18px 24px 0; }
  .situation-strip { max-width: 760px; margin: 18px 24px 0; }
  .filter-bar { max-width: 760px; margin: 0 auto; }
  .filter-panel { max-width: 760px; margin: 10px auto 0; }
}
/* #endif */
</style>
