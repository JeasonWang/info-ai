<script setup lang="ts">
import type { StatsData } from '@/types'

defineProps<{
  stats: StatsData | null
  loading: boolean
}>()
</script>

<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">Overview</p>
        <h2>实时统计</h2>
      </div>
    </div>

    <div v-if="loading" class="empty-state">正在加载统计数据...</div>
    <div v-else-if="stats" class="stats-grid">
      <article class="metric-card metric-card--highlight">
        <span class="metric-card__label">总信息量</span>
        <strong>{{ stats.total }}</strong>
      </article>

      <article
        v-for="item in stats.categories"
        :key="item.name"
        class="metric-card"
      >
        <span class="metric-card__label">{{ item.name }}</span>
        <strong>{{ item.count }}</strong>
      </article>
    </div>
  </section>
</template>
