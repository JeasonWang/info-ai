<script setup lang="ts">
defineProps<{
  active: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()
</script>

<template>
  <button
    type="button"
    :class="['button', active ? 'button--favorite-active' : 'button--favorite']"
    @click.stop="emit('toggle')"
  >
    {{ active ? '已收藏' : '收藏' }}
  </button>
</template>
