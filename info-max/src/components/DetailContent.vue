<script setup lang="ts">
import { computed } from 'vue'
import FormattedContent from '@/components/FormattedContent.vue'
import type { InfoItem } from '@/types'
import { getContentMode, getMediaUrls } from '@/utils'

const props = defineProps<{
  info: InfoItem
  content?: string
}>()

const displayContent = computed(() => props.content ?? props.info.content)
const hasDisplayContent = computed(() => displayContent.value.trim().length > 0)
const contentMode = computed(() => getContentMode(displayContent.value))
const media = computed(() => getMediaUrls(props.info))
</script>

<template>
  <section v-if="hasDisplayContent || media.images.length || media.videos.length" class="panel" data-testid="detail-content">
    <div class="panel__header">
      <div>
        <p class="panel__eyebrow">Content</p>
        <h2>正文</h2>
      </div>
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
      <FormattedContent v-if="hasDisplayContent" :content="displayContent" />
    </article>
  </section>
</template>
