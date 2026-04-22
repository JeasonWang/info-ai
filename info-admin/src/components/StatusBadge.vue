<script setup lang="ts">
defineProps<{
  label: string
  tone?: 'success' | 'warning' | 'muted'
}>()
</script>

<template>
  <span class="status-badge" :class="tone || 'muted'">{{ label }}</span>
</template>
