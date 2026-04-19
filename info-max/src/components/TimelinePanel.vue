<script setup lang="ts">
import type { InfoItem } from '@/types'
import { formatDateTime } from '@/utils'

defineProps<{
  items: InfoItem[]
}>()
</script>

<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">Timeline</p>
        <h2>最新时间线</h2>
      </div>
    </div>

    <div v-if="items.length === 0" class="empty-state">暂无时间线数据</div>
    <div v-else class="timeline">
      <article v-for="item in items" :key="item.id" class="timeline__item">
        <div class="timeline__dot"></div>
        <div class="timeline__content">
          <span class="panel__meta">{{ formatDateTime(item.event_time || item.created_at) }}</span>
          <h3>{{ item.title }}</h3>
          <p>{{ item.channel_name }} · {{ item.category_name }}</p>
        </div>
      </article>
    </div>
  </section>
</template>
