<script setup lang="ts">
import { computed } from 'vue'
import FormattedContent from '@/components/FormattedContent.vue'
import type { InfoItem } from '@/types'
import { getContentMode, getMediaUrls } from '@/utils'

const props = defineProps<{
  info: InfoItem
}>()

const contentMode = computed(() => getContentMode(props.info.content))
const media = computed(() => getMediaUrls(props.info))
</script>

<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">Content</p>
        <h2>正文展示</h2>
      </div>
      <span class="panel__meta">自动识别普通文本 / Markdown / HTML 片段 / 媒体链接</span>
    </div>

    <div v-if="media.images.length" class="media-grid">
      <img v-for="url in media.images" :key="url" :src="url" alt="内容图片" />
    </div>

    <div v-if="media.videos.length" class="media-grid media-grid--videos">
      <video v-for="url in media.videos" :key="url" :src="url" controls />
    </div>

    <article class="content-block">
      <p v-if="contentMode === 'html'" class="content-block__tip">
        检测到 HTML 结构内容，已转换为更适合阅读的文本版。
      </p>
      <FormattedContent :content="info.content" />
    </article>
  </section>
</template>
