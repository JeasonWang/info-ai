<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { Category, Channel } from '@/types'

const props = defineProps<{
  categories: Category[]
  channels: Channel[]
  categoryId?: number
  channelId?: number
  keyword?: string
  busy?: boolean
  activeCategoryName?: string
  activeChannelName?: string
}>()

const emit = defineEmits<{
  search: [
    payload: {
      categoryId?: number
      channelId?: number
      keyword?: string
    },
  ]
  openMenu: []
}>()

const form = reactive({
  categoryId: props.categoryId ? String(props.categoryId) : '',
  channelId: props.channelId ? String(props.channelId) : '',
  keyword: props.keyword ?? '',
})
const expanded = ref(false)

let keywordTimer: ReturnType<typeof setTimeout> | null = null

const categoryTabs = computed(() =>
  props.categories.map((category) => ({
    id: String(category.id),
    name: category.name,
  })),
)

const channelTabs = computed(() =>
  props.channels
    .map((channel) => ({
      id: String(channel.id),
      name: channel.name,
    })),
)

watch(
  () => [props.categoryId, props.channelId, props.keyword],
  ([categoryId, channelId, keyword]) => {
    form.categoryId = categoryId != null ? String(categoryId) : ''
    form.channelId = channelId != null ? String(channelId) : ''
    form.keyword = typeof keyword === 'string' ? keyword : ''
  },
)

function submit() {
  emit('search', {
    categoryId: form.categoryId ? Number(form.categoryId) : undefined,
    channelId: form.channelId ? Number(form.channelId) : undefined,
    keyword: form.keyword.trim() || undefined,
  })
  expanded.value = false
}

function chooseCategory(categoryId: string) {
  if (props.busy) return
  form.categoryId = form.categoryId === categoryId ? '' : categoryId
  form.channelId = ''
  submit()
}

function chooseChannel(channelId: string) {
  if (props.busy) return
  form.channelId = form.channelId === channelId ? '' : channelId
  submit()
}

function queueKeywordSearch() {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => {
    submit()
  }, 350)
}

function clearKeyword() {
  form.keyword = ''
  submit()
}

function resetFilters() {
  form.categoryId = ''
  form.channelId = ''
  form.keyword = ''
  submit()
}

watch(
  () => form.keyword,
  (value, oldValue) => {
    if (value === oldValue) return
    queueKeywordSearch()
  },
)
</script>

<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">Filter</p>
        <h2>内容筛选</h2>
      </div>
      <div class="filter-bar__header-actions">
        <span class="tag">{{ activeCategoryName || '全部分类' }}</span>
        <span class="tag tag--soft">{{ activeChannelName || '全部渠道' }}</span>
        <button
          class="button button--ghost button--small"
          type="button"
          @click="expanded = !expanded"
        >
          {{ expanded ? '收起筛选' : '展开筛选' }}
        </button>
        <button class="button button--ghost button--small" type="button" @click="emit('openMenu')">
          更多内容
        </button>
      </div>
    </div>

    <div v-if="expanded" class="filters">
      <div class="filter-group">
        <span class="filter-group__label">分类</span>
        <div class="tab-list">
          <button
            v-for="category in categoryTabs"
            :key="category.id || 'all-category'"
            :class="['tab-chip', form.categoryId === category.id ? 'tab-chip--active' : '']"
            :disabled="busy"
            @click="chooseCategory(category.id)"
          >
            {{ category.name }}
          </button>
        </div>
      </div>

      <div class="filter-group">
        <span class="filter-group__label">渠道</span>
        <div class="tab-list">
          <button
            v-for="channel in channelTabs"
            :key="channel.id || 'all-channel'"
            :class="['tab-chip', form.channelId === channel.id ? 'tab-chip--active' : '']"
            :disabled="busy"
            @click="chooseChannel(channel.id)"
          >
            {{ channel.name }}
          </button>
        </div>
      </div>

      <label class="field field--search">
        <span>关键词</span>
        <div class="search-box">
          <input
            v-model="form.keyword"
            :disabled="busy"
            type="text"
            placeholder="搜索标题或正文"
            @keyup.enter="submit"
          />
          <button
            v-if="form.keyword"
            class="button button--ghost button--small"
            type="button"
            @click="clearKeyword"
          >
            清空
          </button>
          <button class="button button--ghost button--small" type="button" @click="resetFilters">
            重置
          </button>
        </div>
      </label>
    </div>
  </section>
</template>
