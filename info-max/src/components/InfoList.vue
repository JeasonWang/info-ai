<script setup lang="ts">
import { RouterLink, useRouter } from 'vue-router'
import FavoriteButton from '@/components/FavoriteButton.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import type { InfoItem } from '@/types'
import { formatDateTime, getStatusTone, summarize } from '@/utils'

const router = useRouter()

defineProps<{
  items: InfoItem[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  favoritesSet: Set<number>
  hasFilters: boolean
}>()

const emit = defineEmits<{
  pageChange: [page: number]
  toggleFavorite: [id: number]
  retry: []
}>()

function openDetail(id: number) {
  router.push(`/info/${id}`)
}
</script>

<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">List</p>
        <h2>内容列表</h2>
      </div>
      <span class="panel__meta">共 {{ total }} 条</span>
    </div>

    <div v-if="loading" class="card-stack">
      <SkeletonBlock v-for="item in 4" :key="item" :lines="4" />
    </div>
    <div v-else-if="items.length === 0" class="empty-state empty-state--rich">
      <strong>{{ hasFilters ? '当前筛选条件下暂无内容' : '当前还没有可展示的信息' }}</strong>
      <p>{{ hasFilters ? '可以调整分类、渠道或关键词后再试一次。' : '后端爬虫可能还在初始化，可以稍后刷新。' }}</p>
      <button class="button button--ghost" @click="emit('retry')">重新加载</button>
    </div>
    <div v-else class="card-stack">
      <article
        v-for="item in items"
        :key="item.id"
        class="info-card info-card--interactive"
        role="link"
        tabindex="0"
        @click="openDetail(item.id)"
        @keydown.enter="openDetail(item.id)"
        @keydown.space.prevent="openDetail(item.id)"
      >
        <div class="info-card__top">
          <div class="tags">
            <span class="tag">{{ item.category_name }}</span>
            <span class="tag tag--soft">{{ item.channel_name }}</span>
            <span :class="['tag', `tag--${getStatusTone(item.detail_fetch_status)}`]">
              {{ item.detail_fetch_status }}
            </span>
          </div>
          <span class="panel__meta">{{ formatDateTime(item.event_time || item.created_at) }}</span>
        </div>

        <h3>{{ item.title }}</h3>
        <p class="info-card__summary">{{ summarize(item.content || '暂无正文') }}</p>

        <div class="info-card__meta">
          <span v-if="item.core_entity">主体：{{ item.core_entity }}</span>
          <span v-if="item.location">地点：{{ item.location }}</span>
          <span v-if="item.indicator_name">指标：{{ item.indicator_name }} {{ item.indicator_value }}</span>
        </div>

        <div class="info-card__actions">
          <FavoriteButton :active="favoritesSet.has(item.id)" @toggle="emit('toggleFavorite', item.id)" />
          <a
            v-if="item.source_url"
            class="button button--ghost"
            :href="item.source_url"
            target="_blank"
            rel="noreferrer"
            @click.stop
          >
            查看原文
          </a>
          <RouterLink class="button button--primary" :to="`/info/${item.id}`" @click.stop>
            查看详情
          </RouterLink>
        </div>
      </article>
    </div>

    <PaginationBar
      v-if="!loading && total > pageSize"
      :page="page"
      :page-size="pageSize"
      :total="total"
      :loading="loading"
      @change="emit('pageChange', $event)"
    />
  </section>
</template>
