export type HomeSortMode = 'composite' | 'latest'

export interface HomeFilterMemory {
  categoryCode: string
  sortMode: HomeSortMode
  keyword: string
}

const STORAGE_KEY = 'info-daren:home-filter-memory'

function isHomeSortMode(value: unknown): value is HomeSortMode {
  return value === 'composite' || value === 'latest'
}

export function loadHomeFilterMemory(): HomeFilterMemory {
  if (typeof window === 'undefined') {
    return { categoryCode: 'all', sortMode: 'composite', keyword: '' }
  }

  try {
    const rawValue = window.localStorage.getItem(STORAGE_KEY)
    if (!rawValue) {
      return { categoryCode: 'all', sortMode: 'composite', keyword: '' }
    }
    const parsed = JSON.parse(rawValue) as Partial<HomeFilterMemory>
    return {
      categoryCode: typeof parsed.categoryCode === 'string' && parsed.categoryCode ? parsed.categoryCode : 'all',
      sortMode: isHomeSortMode(parsed.sortMode) ? parsed.sortMode : 'composite',
      keyword: typeof parsed.keyword === 'string' ? parsed.keyword : '',
    }
  } catch {
    return { categoryCode: 'all', sortMode: 'composite', keyword: '' }
  }
}

export function saveHomeFilterMemory(memory: HomeFilterMemory) {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(memory))
}
