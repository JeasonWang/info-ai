<script setup lang="ts">
import { RouterLink } from 'vue-router'
import PaginationBar from '@/components/PaginationBar.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import type { EventListItem } from '@/types'
import { formatDateTime } from '@/utils'

defineProps<{
  items: EventListItem[]
  loading: boolean
  total: number
  page: number
  pageSize: number
}>()

const emit = defineEmits<{
  pageChange: [page: number]
  retry: []
}>()
</script>

<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">Events</p>
        <h2>热点事件流</h2>
      </div>
      <span class="panel__meta">共 {{ total }} 条事件</span>
    </div>

    <div v-if="loading" class="card-stack">
      <SkeletonBlock v-for="item in 4" :key="item" :lines="4" />
    </div>
    <div v-else-if="items.length === 0" class="empty-state empty-state--rich">
      <strong>当前还没有可展示的热点事件</strong>
      <p>你可以稍后重试，或者先去后台触发一次事件重建。</p>
      <button class="button button--ghost" type="button" @click="emit('retry')">重新加载</button>
    </div>
    <div v-else class="card-stack">
      <article v-for="item in items" :key="item.id" class="info-card">
        <div class="info-card__top">
          <div class="tags">
            <span class="tag">{{ item.primary_category.name }}</span>
            <span class="tag tag--soft">热度 {{ item.heat_score }}</span>
            <span class="tag tag--soft">时效 {{ item.freshness_score }}</span>
          </div>
          <span class="panel__meta">{{ formatDateTime(item.last_updated_at) }}</span>
        </div>

        <h3>{{ item.title }}</h3>
        <p class="info-card__summary">{{ item.one_line_summary }}</p>

        <div class="info-card__meta">
          <span>来源 {{ item.source_count }} 个</span>
          <span v-if="item.new_update_count > 0">{{ item.new_update_count }} 条新进展</span>
        </div>

        <div class="tags">
          <span v-for="badge in item.source_badges" :key="badge" class="tag tag--soft">
            {{ badge }}
          </span>
        </div>

        <div class="info-card__actions">
          <RouterLink class="button button--primary" :to="`/events/${item.id}`">
            看时间线
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
