<script setup lang="ts">
import type { EventTimelineItem } from '@/types'
import { formatDateTime } from '@/utils'

defineProps<{
  items: EventTimelineItem[]
}>()
</script>

<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">Timeline</p>
        <h2>事件时间线</h2>
      </div>
    </div>

    <div v-if="items.length === 0" class="empty-state">暂时还没有可展示的时间线节点。</div>
    <div v-else class="timeline event-timeline">
      <article v-for="item in items" :key="item.id" class="timeline__item event-timeline__item">
        <div class="timeline__dot"></div>
        <div class="timeline__content">
          <span class="panel__meta">{{ formatDateTime(item.occurred_at) }}</span>
          <h3>{{ item.summary }}</h3>
          <p>可信度 {{ Math.round(item.confidence * 100) }}%</p>
        </div>
      </article>
    </div>
  </section>
</template>
