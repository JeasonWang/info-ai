<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import EventCategoryTabs from '@/components/EventCategoryTabs.vue'
import EventList from '@/components/EventList.vue'
import { getEventCategories, getEvents } from '@/services/api'
import type { EventCategory, EventPage } from '@/types'

const pageSize = 10
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const loadMoreError = ref('')
const categories = ref<EventCategory[]>([])
const activeCategoryCode = ref('all')
const keyword = ref('')
const appliedKeyword = ref('')
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
const hasMore = computed(() => eventPage.value.items.length < eventPage.value.total)

async function loadCategories() {
  categories.value = await getEventCategories()
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
  await loadEvents(1)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submitSearch() {
  appliedKeyword.value = keyword.value.trim()
  await loadEvents(1)
}

async function loadHome() {
  try {
    await loadCategories()
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
    </section>

    <section class="home-channel-strip" data-testid="home-channel-strip">
      <EventCategoryTabs
        :categories="categories"
        :active-code="activeCategoryCode"
        @select="selectCategory"
      />
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
