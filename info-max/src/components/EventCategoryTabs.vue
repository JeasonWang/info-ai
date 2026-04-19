<script setup lang="ts">
import type { EventCategory } from '@/types'

defineProps<{
  categories: EventCategory[]
  activeCode: string
}>()

const emit = defineEmits<{
  select: [code: string]
}>()
</script>

<template>
  <div class="event-tabs" role="tablist" aria-label="热点分类">
    <button
      v-for="category in categories"
      :key="category.code"
      :class="['event-tab', category.code === activeCode ? 'event-tab--active' : '']"
      :data-code="category.code"
      type="button"
      @click="emit('select', category.code)"
    >
      {{ category.name }}
    </button>
  </div>
</template>
