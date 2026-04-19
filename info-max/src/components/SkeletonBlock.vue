<script setup lang="ts">
defineProps<{
  lines?: number
  compact?: boolean
}>()
</script>

<template>
  <div class="skeleton-card">
    <div class="skeleton skeleton--title"></div>
    <div
      v-for="line in lines ?? 3"
      :key="line"
      :class="['skeleton', compact ? 'skeleton--compact' : '']"
    ></div>
  </div>
</template>
