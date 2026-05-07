<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  page: number
  pageSize: number
  total: number
}>()

const emit = defineEmits<{
  'update:page': [value: number]
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const start = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const end = computed(() => Math.min(props.total, props.page * props.pageSize))

function goTo(page: number) {
  const nextPage = Math.min(totalPages.value, Math.max(1, page))
  emit('update:page', nextPage)
}
</script>

<template>
  <div v-if="total > pageSize" class="pagination-control">
    <span>显示 {{ start }}-{{ end }} / {{ total }}</span>
    <div>
      <button class="button button--ghost" type="button" :disabled="page <= 1" @click="goTo(page - 1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button class="button button--ghost" type="button" :disabled="page >= totalPages" @click="goTo(page + 1)">下一页</button>
    </div>
  </div>
</template>
