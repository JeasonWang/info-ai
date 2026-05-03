import { ref } from 'vue'

const STORAGE_KEY = 'home_filter_memory'

export interface HomeFilterMemory {
  categoryCode: string
  sortMode: 'composite' | 'latest'
  keyword: string
}

const DEFAULT: HomeFilterMemory = {
  categoryCode: 'all',
  sortMode: 'composite',
  keyword: '',
}

export function useFilterMemory() {
  const memory = ref<HomeFilterMemory>(load())

  function load(): HomeFilterMemory {
    try {
      const raw = uni.getStorageSync(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        return { ...DEFAULT, ...parsed }
      }
    } catch {
      // ignore
    }
    return { ...DEFAULT }
  }

  function save(value: HomeFilterMemory) {
    memory.value = value
    uni.setStorageSync(STORAGE_KEY, JSON.stringify(value))
  }

  return {
    memory,
    save,
  }
}
