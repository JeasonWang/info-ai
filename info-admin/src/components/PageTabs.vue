<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  items: Array<{
    to: string
    label: string
    description?: string
  }>
}>()
</script>

<template>
  <nav class="page-tabs" aria-label="页面分区">
    <RouterLink v-for="item in items" :key="item.to" class="page-tab" :to="item.to">
      <strong>{{ item.label }}</strong>
      <span v-if="item.description">{{ item.description }}</span>
    </RouterLink>
  </nav>
</template>
