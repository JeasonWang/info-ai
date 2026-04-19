import { computed, ref } from 'vue'

const STORAGE_KEY = 'info-max:favorites'
const favoriteIds = ref<number[]>([])
let initialized = false

function loadFavorites() {
  if (initialized || typeof window === 'undefined') return
  initialized = true

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    favoriteIds.value = raw ? JSON.parse(raw) : []
  } catch {
    favoriteIds.value = []
  }
}

function persistFavorites() {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(favoriteIds.value))
}

export function useFavorites() {
  loadFavorites()

  const favoritesSet = computed(() => new Set(favoriteIds.value))

  function isFavorite(id: number) {
    return favoritesSet.value.has(id)
  }

  function toggleFavorite(id: number) {
    if (favoritesSet.value.has(id)) {
      favoriteIds.value = favoriteIds.value.filter((item) => item !== id)
    } else {
      favoriteIds.value = [...favoriteIds.value, id]
    }
    persistFavorites()
  }

  return {
    favoriteIds,
    favoritesSet,
    favoritesCount: computed(() => favoriteIds.value.length),
    isFavorite,
    toggleFavorite,
  }
}
