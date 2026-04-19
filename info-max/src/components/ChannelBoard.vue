<script setup lang="ts">
import { ref } from 'vue'
import type { Channel } from '@/types'
import { triggerCrawl } from '@/services/api'

defineProps<{
  channels: Channel[]
}>()

const activeChannelCode = ref('')
const feedback = ref('')

async function handleTrigger(channel: Channel) {
  activeChannelCode.value = channel.code
  feedback.value = ''

  try {
    const result = await triggerCrawl(channel.code)
    feedback.value = `${channel.name} 已触发，抓取 ${result.raw_count} 条，清洗 ${result.cleaned_count} 条，详情拉取 ${result.detail_fetched} 条。`
  } catch (error) {
    feedback.value = error instanceof Error ? error.message : '触发失败'
  } finally {
    activeChannelCode.value = ''
  }
}
</script>

<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">Channels</p>
        <h2>渠道运维</h2>
      </div>
      <span class="panel__meta">可直接触发后端爬取</span>
    </div>

    <div class="channel-grid">
      <article v-for="channel in channels" :key="channel.id" class="channel-card">
        <div>
          <h3>{{ channel.name }}</h3>
          <p class="channel-card__url">{{ channel.base_url }}</p>
        </div>
        <div class="channel-card__meta">
          <span>编码：{{ channel.code }}</span>
          <span>间隔：{{ channel.crawl_interval }} 分钟</span>
        </div>
        <button
          class="button button--ghost"
          :disabled="activeChannelCode === channel.code"
          @click="handleTrigger(channel)"
        >
          {{ activeChannelCode === channel.code ? '执行中...' : '触发爬取' }}
        </button>
      </article>
    </div>

    <p v-if="feedback" class="feedback">{{ feedback }}</p>
  </section>
</template>
