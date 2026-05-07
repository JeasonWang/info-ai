<script setup lang="ts">
defineProps<{
  title: string
  status?: string
}>()
</script>

<template>
  <article class="panel">
    <div class="panel-title">
      <h3>{{ title }}</h3>
      <span v-if="status">{{ status }}</span>
    </div>
    <slot />
  </article>
</template>
