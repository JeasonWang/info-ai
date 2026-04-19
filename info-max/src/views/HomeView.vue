<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import ChannelBoard from '@/components/ChannelBoard.vue'
import FilterBar from '@/components/FilterBar.vue'
import InfoList from '@/components/InfoList.vue'
import { useFavorites } from '@/composables/useFavorites'
import { getCategories, getChannels, getInfos } from '@/services/api'
import type { Category, Channel, InfoPage } from '@/types'

const categories = ref<Category[]>([])
const channels = ref<Channel[]>([])
const infoPage = ref<InfoPage>({
  total: 0,
  page: 1,
  page_size: 20,
  items: [],
})
const loading = ref(false)
const error = ref('')
const pageSize = 12
const menuOpen = ref(false)
const query = ref<{
  categoryId?: number
  channelId?: number
  keyword?: string
  page: number
}>({
  page: 1,
})
const { favoritesSet, favoritesCount, toggleFavorite } = useFavorites()

const hasFilters = computed(() => Boolean(query.value.categoryId || query.value.channelId || query.value.keyword))
const activeChannelName = computed(
  () => channels.value.find((item) => item.id === query.value.channelId)?.name ?? '全部渠道',
)
const activeCategoryName = computed(
  () => categories.value.find((item) => item.id === query.value.categoryId)?.name ?? '全部分类',
)

async function loadMeta() {
  const [categoryData, channelData] = await Promise.all([getCategories(), getChannels()])
  categories.value = categoryData
  channels.value = channelData
}

async function loadInfos() {
  loading.value = true
  error.value = ''
  try {
    infoPage.value = await getInfos({
      category_id: query.value.categoryId,
      channel_id: query.value.channelId,
      keyword: query.value.keyword,
      page: query.value.page,
      page_size: pageSize,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function applyFilters(payload: {
  categoryId?: number
  channelId?: number
  keyword?: string
}) {
  query.value = {
    ...payload,
    page: 1,
  }
  await loadInfos()
}

async function handlePageChange(page: number) {
  query.value = {
    ...query.value,
    page,
  }
  await loadInfos()
}

watch(
  () => query.value.categoryId,
  async (categoryId) => {
    channels.value = await getChannels(categoryId)
    if (query.value.channelId && !channels.value.some((item) => item.id === query.value.channelId)) {
      query.value = {
        ...query.value,
        channelId: undefined,
      }
      await loadInfos()
    }
  },
)

onMounted(async () => {
  try {
    await loadMeta()
    await loadInfos()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '初始化失败'
  }
})
</script>

<template>
  <div class="dashboard">
    <div class="dashboard__filter-shell">
      <FilterBar
        :categories="categories"
        :channels="channels"
        :category-id="query.categoryId"
        :channel-id="query.channelId"
        :keyword="query.keyword"
        :busy="loading"
        :active-category-name="activeCategoryName"
        :active-channel-name="activeChannelName"
        @search="applyFilters"
        @open-menu="menuOpen = true"
      />
    </div>

    <p v-if="error" class="error-banner">{{ error }}</p>

    <div class="dashboard__main">
      <InfoList
        class="dashboard__list"
        :items="infoPage.items"
        :loading="loading"
        :total="infoPage.total"
        :page="infoPage.page"
        :page-size="infoPage.page_size"
        :favorites-set="favoritesSet"
        :has-filters="hasFilters"
        @page-change="handlePageChange"
        @toggle-favorite="toggleFavorite"
        @retry="loadInfos"
      />
    </div>

    <div v-if="menuOpen" class="drawer-backdrop" @click="menuOpen = false"></div>
    <aside :class="['drawer', menuOpen ? 'drawer--open' : '']" aria-label="更多内容">
      <div class="drawer__header">
        <div>
          <p class="panel__eyebrow">More</p>
          <h2>更多内容</h2>
        </div>
        <button class="button button--ghost button--small" type="button" @click="menuOpen = false">
          关闭
        </button>
      </div>

      <div class="drawer__content">
        <section class="panel">
          <div class="panel__header">
            <div>
              <p class="panel__eyebrow">Admin</p>
              <h2>管理入口</h2>
            </div>
          </div>
          <RouterLink class="button button--primary" to="/settings" @click="menuOpen = false">
            打开配置管理
          </RouterLink>
        </section>

        <section class="panel panel--compact dashboard__summary dashboard__summary--inside">
          <div>
            <p class="panel__eyebrow">Personal</p>
            <h2>我的阅读状态</h2>
          </div>
          <div class="dashboard__summary-stats">
            <span class="tag tag--soft">已收藏 {{ favoritesCount }} 条</span>
            <span class="panel__meta">收藏保存在当前浏览器，本地可持续保留。</span>
          </div>
        </section>
        <ChannelBoard :channels="channels" />
      </div>
    </aside>
  </div>
</template>
