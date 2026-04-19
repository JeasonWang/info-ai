<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  page: number
  pageSize: number
  total: number
  loading?: boolean
}>()

const emit = defineEmits<{
  change: [page: number]
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const pageItems = computed(() => {
  const pages: Array<number | string> = []
  const current = props.page
  const total = totalPages.value

  if (total <= 7) {
    return Array.from({ length: total }, (_, index) => index + 1)
  }

  pages.push(1)

  if (current > 3) pages.push('...')

  for (let page = Math.max(2, current - 1); page <= Math.min(total - 1, current + 1); page += 1) {
    pages.push(page)
  }

  if (current < total - 2) pages.push('...')
  pages.push(total)

  return pages
})

function changePage(page: number) {
  if (page < 1 || page > totalPages.value || page === props.page) return
  emit('change', page)
}
</script>

<template>
  <div class="pagination">
    <button class="button button--ghost" :disabled="loading || page <= 1" @click="changePage(page - 1)">
      上一页
    </button>

    <div class="pagination__pages">
      <button
        v-for="(item, index) in pageItems"
        :key="`${item}-${index}`"
        :class="[
          'pagination__page',
          typeof item === 'number' && item === page ? 'pagination__page--active' : '',
          typeof item === 'string' ? 'pagination__page--ellipsis' : '',
        ]"
        :disabled="loading || typeof item !== 'number'"
        @click="typeof item === 'number' && changePage(item)"
      >
        {{ item }}
      </button>
    </div>

    <span class="panel__meta">第 {{ page }} / {{ totalPages }} 页</span>

    <button
      class="button button--ghost"
      :disabled="loading || page >= totalPages"
      @click="changePage(page + 1)"
    >
      下一页
    </button>
  </div>
</template>
