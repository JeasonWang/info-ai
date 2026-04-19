<script setup lang="ts">
import type { EventSourceView } from '@/types'

defineProps<{
  summaries: Record<string, string>
  sourceViews: EventSourceView[]
}>()
</script>

<template>
  <div class="detail-summary-stack">
    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="panel__eyebrow">Summary</p>
          <h2>事件解读</h2>
        </div>
      </div>

      <div class="summary-grid">
        <article class="summary-card">
          <h3>发生了什么</h3>
          <p>{{ summaries.what_happened || '暂未生成摘要。' }}</p>
        </article>
        <article class="summary-card">
          <h3>为什么重要</h3>
          <p>{{ summaries.why_it_matters || '暂未生成摘要。' }}</p>
        </article>
        <article class="summary-card">
          <h3>最新进展</h3>
          <p>{{ summaries.latest_update || '暂未生成摘要。' }}</p>
        </article>
      </div>
    </section>

    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="panel__eyebrow">Views</p>
          <h2>多平台怎么说</h2>
        </div>
      </div>

      <div v-if="sourceViews.length === 0" class="empty-state">暂时还没有聚合出多平台观点。</div>
      <div v-else class="source-view-list">
        <article v-for="item in sourceViews" :key="item.channel_name" class="summary-card">
          <h3>{{ item.channel_name }}</h3>
          <p>{{ item.summary }}</p>
        </article>
      </div>
    </section>
  </div>
</template>
