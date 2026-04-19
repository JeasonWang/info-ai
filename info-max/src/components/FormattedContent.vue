<script setup lang="ts">
import { computed } from 'vue'
import { formatRichContent } from '@/utils'

const props = defineProps<{
  content: string
}>()

const blocks = computed(() => formatRichContent(props.content))
</script>

<template>
  <div class="formatted-content">
    <template v-for="(block, index) in blocks" :key="`${block.type}-${index}`">
      <h3 v-if="block.type === 'heading'" class="formatted-content__heading">
        {{ block.text }}
      </h3>

      <ul v-else-if="block.type === 'list'" class="formatted-content__list">
        <li v-for="item in block.items" :key="item">{{ item }}</li>
      </ul>

      <blockquote v-else-if="block.type === 'quote'" class="formatted-content__quote">
        {{ block.text }}
      </blockquote>

      <pre v-else-if="block.type === 'code'" class="formatted-content__code">{{ block.text }}</pre>

      <p v-else class="formatted-content__paragraph">
        <template v-for="(segment, segmentIndex) in block.segments" :key="`${segment.text}-${segmentIndex}`">
          <a
            v-if="segment.kind === 'link'"
            :href="segment.text"
            target="_blank"
            rel="noreferrer"
            class="formatted-content__link"
          >
            {{ segment.text }}
          </a>
          <span
            v-else-if="segment.kind === 'hashtag'"
            class="formatted-content__hashtag"
          >
            {{ segment.text }}
          </span>
          <span v-else>{{ segment.text }}</span>
        </template>
      </p>
    </template>
  </div>
</template>
