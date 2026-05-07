import { ref } from 'vue'

export interface ListLoadOptions {
  pageSize?: number
}

export function useListLoad<T>(
  fetcher: (page: number, pageSize: number) => Promise<{ items: T[]; total: number }>,
  options: ListLoadOptions = {},
) {
  const pageSize = options.pageSize || 10
  const list = ref<T[]>([])
  const total = ref(0)
  const page = ref(1)
  const loading = ref(false)
  const hasMore = ref(true)
  const error = ref('')

  async function loadMore() {
    if (loading.value || !hasMore.value) return
    loading.value = true
    error.value = ''

    try {
      const result = await fetcher(page.value, pageSize)
      total.value = result.total
      if (page.value === 1) {
        list.value = result.items
      } else {
        list.value.push(...result.items)
      }
      hasMore.value = list.value.length < result.total
      if (hasMore.value) {
        page.value++
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function refresh() {
    page.value = 1
    hasMore.value = true
    list.value = []
    total.value = 0
    await loadMore()
  }

  return {
    list,
    total,
    page,
    loading,
    hasMore,
    error,
    loadMore,
    refresh,
  }
}
