<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import EventCategoryTabs from '@/components/EventCategoryTabs.vue'
import EventList from '@/components/EventList.vue'
import { getEventCategories, getEvents } from '@/services/api'
import { loadHomeFilterMemory, saveHomeFilterMemory } from '@/services/homeFilterMemory'
import type { EventCategory, EventPage } from '@/types'

const pageSize = 10
const filterMemory = loadHomeFilterMemory()
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const loadMoreError = ref('')
const categories = ref<EventCategory[]>([])
const activeCategoryCode = ref(filterMemory.categoryCode)
const keyword = ref(filterMemory.keyword)
const appliedKeyword = ref(filterMemory.keyword)
const sortMode = ref<'composite' | 'latest'>(filterMemory.sortMode)
const filterExpanded = ref(false)
const showBackToTop = ref(false)
const loadMoreSentinel = ref<HTMLElement | null>(null)
let loadMoreObserver: IntersectionObserver | null = null
const eventPage = ref<EventPage>({
  total: 0,
  page: 1,
  page_size: pageSize,
  items: [],
})

const activeCategoryName = computed(
  () => categories.value.find((item) => item.code === activeCategoryCode.value)?.name ?? '全网',
)
const sortModeLabel = computed(() => (sortMode.value === 'latest' ? '最新更新优先' : '综合分优先'))
const hasMore = computed(() => eventPage.value.items.length < eventPage.value.total)

async function loadCategories() {
  categories.value = await getEventCategories()
  const categoryExists = categories.value.some((item) => item.code === activeCategoryCode.value)
  if (!categoryExists) {
    activeCategoryCode.value = 'all'
  }
}

function rememberCurrentFilter() {
  saveHomeFilterMemory({
    categoryCode: activeCategoryCode.value,
    sortMode: sortMode.value,
    keyword: appliedKeyword.value,
  })
}

async function loadEvents(page = 1, mode: 'replace' | 'append' = 'replace') {
  if (mode === 'append') {
    loadingMore.value = true
    loadMoreError.value = ''
  } else {
    loading.value = true
    error.value = ''
    loadMoreError.value = ''
  }

  try {
    const nextPage = await getEvents({
      category_code: activeCategoryCode.value,
      keyword: appliedKeyword.value,
      sort: sortMode.value,
      page,
      page_size: pageSize,
    })
    eventPage.value = {
      ...nextPage,
      items: mode === 'append' ? [...eventPage.value.items, ...nextPage.items] : nextPage.items,
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : '加载热点事件失败'
    if (mode === 'append') {
      loadMoreError.value = message
    } else {
      error.value = message
    }
  } finally {
    if (mode === 'append') {
      loadingMore.value = false
    } else {
      loading.value = false
    }
  }
}

async function loadMoreEvents() {
  if (loading.value || loadingMore.value || !hasMore.value) {
    return
  }
  await loadEvents(eventPage.value.page + 1, 'append')
}

async function selectCategory(code: string) {
  if (code === activeCategoryCode.value) return
  activeCategoryCode.value = code
  rememberCurrentFilter()
  await loadEvents(1)
  filterExpanded.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submitSearch() {
  appliedKeyword.value = keyword.value.trim()
  rememberCurrentFilter()
  await loadEvents(1)
}

async function selectSort(mode: 'composite' | 'latest') {
  if (mode === sortMode.value) return
  sortMode.value = mode
  rememberCurrentFilter()
  await loadEvents(1)
  filterExpanded.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function toggleFilterPanel() {
  filterExpanded.value = !filterExpanded.value
}

async function loadHome() {
  try {
    await loadCategories()
    rememberCurrentFilter()
    await loadEvents()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '首页初始化失败'
  }
}

function handleScroll() {
  showBackToTop.value = window.scrollY > 360
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function setupLoadMoreObserver() {
  if (!loadMoreSentinel.value || typeof IntersectionObserver === 'undefined') {
    return
  }
  loadMoreObserver?.disconnect()
  loadMoreObserver = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      loadMoreEvents()
    }
  }, { rootMargin: '180px 0px' })
  loadMoreObserver.observe(loadMoreSentinel.value)
}

onMounted(() => {
  loadHome()
  handleScroll()
  window.addEventListener('scroll', handleScroll, { passive: true })
  setupLoadMoreObserver()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
  loadMoreObserver?.disconnect()
})
</script>

<template>
  <div class="dashboard dashboard--events">
    <section class="home-compact-header panel" data-testid="home-compact-header">
      <div class="home-compact-header__title-row">
        <div>
          <p class="panel__eyebrow">Events</p>
          <h1>热点事件</h1>
        </div>
        <span class="home-compact-header__count">
          {{ activeCategoryName }} · {{ eventPage.total }} 条
        </span>
      </div>

      <form class="home-compact-header__search search-box" @submit.prevent="submitSearch">
        <input
          v-model="keyword"
          type="search"
          placeholder="搜索热点事件"
          aria-label="搜索热点事件"
        />
        <button class="button button--primary button--small" type="submit">搜</button>
      </form>

      <div class="home-channel-strip" data-testid="home-channel-strip">
        <button
          type="button"
          class="home-filter-summary"
          data-testid="home-filter-toggle"
          :aria-expanded="filterExpanded"
          @click="toggleFilterPanel"
        >
          <span>当前：{{ activeCategoryName }} · {{ sortModeLabel }}</span>
          <strong>{{ filterExpanded ? '收起' : '调整' }}</strong>
        </button>

        <div v-if="filterExpanded" class="home-filter-panel" data-testid="home-filter-panel">
          <EventCategoryTabs
            :categories="categories"
            :active-code="activeCategoryCode"
            @select="selectCategory"
          />
          <div class="home-sort-switch" aria-label="热点排序方式">
            <button
              type="button"
              class="home-sort-switch__item"
              :class="{ 'home-sort-switch__item--active': sortMode === 'composite' }"
              data-sort="composite"
              @click="selectSort('composite')"
            >
              综合分优先
            </button>
            <button
              type="button"
              class="home-sort-switch__item"
              :class="{ 'home-sort-switch__item--active': sortMode === 'latest' }"
              data-sort="latest"
              @click="selectSort('latest')"
            >
              最新更新优先
            </button>
          </div>
        </div>
      </div>
    </section>

    <p v-if="error" class="error-banner">{{ error }}</p>

    <EventList
      :items="eventPage.items"
      :loading="loading"
      :total="eventPage.total"
      :has-more="hasMore"
      :loading-more="loadingMore"
      :load-more-error="loadMoreError"
      @retry="loadEvents(eventPage.page)"
      @retry-load-more="loadMoreEvents"
    />

    <div ref="loadMoreSentinel" class="load-more-sentinel" data-testid="load-more-sentinel" />

    <button
      v-if="showBackToTop"
      class="back-to-top"
      type="button"
      data-testid="back-to-top"
      aria-label="回到顶部"
      @click="scrollToTop"
    >
      ↑
    </button>
  </div>
</template>
