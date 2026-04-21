<script setup lang="ts">
import { RouterLink } from 'vue-router'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import type { EventListItem } from '@/types'
import { formatDateTime } from '@/utils'

defineProps<{
  items: EventListItem[]
  loading: boolean
  total: number
  hasMore: boolean
  loadingMore: boolean
  loadMoreError: string
}>()

const emit = defineEmits<{
  retry: []
  retryLoadMore: []
}>()
</script>

<template>
  <section class="panel event-list-panel">
    <div v-if="loading" class="card-stack">
      <SkeletonBlock v-for="item in 4" :key="item" :lines="4" />
    </div>
    <div v-else-if="items.length === 0" class="empty-state empty-state--rich">
      <strong>当前还没有可展示的热点事件</strong>
      <p>你可以稍后重试，或者先去后台触发一次事件重建。</p>
      <button class="button button--ghost" type="button" @click="emit('retry')">重新加载</button>
    </div>
    <div v-else class="card-stack">
      <article v-for="item in items" :key="item.id" class="info-card event-card event-card--compact">
        <div class="event-card__meta" data-testid="event-card-meta">
          <span class="tag">{{ item.primary_category.name }}</span>
          <span class="event-card__time">
            {{ item.source_badges[0] || '来源待确认' }} · {{ formatDateTime(item.last_updated_at) }}
          </span>
        </div>

        <RouterLink
          class="event-card__title-link"
          :to="item.representative_info_id ? `/info/${item.representative_info_id}` : `/events/${item.id}`"
        >
          <h3>{{ item.title }}</h3>
        </RouterLink>

        <p
          v-if="item.one_line_summary && item.one_line_summary !== item.title"
          class="info-card__summary event-card__summary"
        >
          {{ item.one_line_summary }}
        </p>

        <div class="event-card__signal" data-testid="event-card-signal">
          热度 {{ item.heat_score }} · {{ item.source_count }} 来源 ·
          {{ item.new_update_count > 0 ? `新增 ${item.new_update_count}` : '持续跟进' }}
        </div>

        <div class="info-card__actions event-card__actions event-card__actions--compact">
          <RouterLink
            class="button button--primary button--small"
            :to="item.representative_info_id ? `/info/${item.representative_info_id}` : `/events/${item.id}`"
          >
            查看详情
          </RouterLink>
          <RouterLink class="event-card__timeline-link" :to="`/events/${item.id}`">
            时间线
          </RouterLink>
        </div>
      </article>
    </div>

    <div v-if="!loading && items.length > 0" class="infinite-status" data-testid="infinite-status">
      <span v-if="loadingMore">正在加载更多热点...</span>
      <template v-else-if="loadMoreError">
        <span>{{ loadMoreError }}</span>
        <button class="button button--ghost button--small" type="button" @click="emit('retryLoadMore')">
          重新加载
        </button>
      </template>
      <span v-else-if="!hasMore">已经看完本频道</span>
    </div>
  </section>
</template>
