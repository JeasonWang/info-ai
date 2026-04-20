<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EventCategoryTabs from '@/components/EventCategoryTabs.vue'
import EventList from '@/components/EventList.vue'
import { getEventCategories, getEvents } from '@/services/api'
import type { EventCategory, EventPage } from '@/types'

const pageSize = 10
const loading = ref(false)
const error = ref('')
const categories = ref<EventCategory[]>([])
const activeCategoryCode = ref('all')
const keyword = ref('')
const appliedKeyword = ref('')
const eventPage = ref<EventPage>({
  total: 0,
  page: 1,
  page_size: pageSize,
  items: [],
})

const activeCategoryName = computed(
  () => categories.value.find((item) => item.code === activeCategoryCode.value)?.name ?? '全网',
)

async function loadCategories() {
  categories.value = await getEventCategories()
}

async function loadEvents(page = 1) {
  loading.value = true
  error.value = ''

  try {
    eventPage.value = await getEvents({
      category_code: activeCategoryCode.value,
      keyword: appliedKeyword.value,
      page,
      page_size: pageSize,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载热点事件失败'
  } finally {
    loading.value = false
  }
}

async function selectCategory(code: string) {
  if (code === activeCategoryCode.value) return
  activeCategoryCode.value = code
  await loadEvents(1)
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

onMounted(loadHome)
</script>

<template>
  <div class="dashboard dashboard--events">
    <section class="panel event-hero">
      <div class="event-hero__copy">
        <p class="panel__eyebrow">Info Daren</p>
        <h1>一句话刷懂全网热点</h1>
        <p class="event-hero__summary">
          默认按热度和时效混合排序，把同一件事在多个平台的更新聚成一个事件，让你不用来回切平台。
        </p>
      </div>

      <div class="event-hero__actions">
        <div class="event-hero__metric">
          <span>当前频道</span>
          <strong>{{ activeCategoryName }}</strong>
        </div>
        <div class="event-hero__metric">
          <span>事件数量</span>
          <strong>{{ eventPage.total }}</strong>
        </div>
      </div>

      <form class="event-hero__search search-box" @submit.prevent="submitSearch">
        <input
          v-model="keyword"
          type="search"
          placeholder="搜索当前频道的热点事件"
          aria-label="搜索当前频道的热点事件"
        />
        <button class="button button--primary" type="submit">搜索</button>
      </form>
    </section>

    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="panel__eyebrow">Categories</p>
          <h2>热点频道</h2>
        </div>
        <span class="panel__meta">先刷全网，再按兴趣切频道</span>
      </div>
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
      :page="eventPage.page"
      :page-size="eventPage.page_size"
      @page-change="loadEvents"
      @retry="loadEvents(eventPage.page)"
    />
  </div>
</template>
