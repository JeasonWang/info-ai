import { computed, ref } from 'vue'
import { addFavoriteEvent, getFavoriteEventIds, removeFavoriteEvent } from '@/services/api'
import { getUserToken } from '@/services/userSession'

const STORAGE_KEY = 'info-max:event-favorites'
const favoriteEventIds = ref<number[]>([])
let initialized = false

function loadLocalEventFavorites() {
  if (initialized || typeof window === 'undefined') return
  initialized = true

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    favoriteEventIds.value = raw ? JSON.parse(raw) : []
  } catch {
    favoriteEventIds.value = []
  }
}

function persistLocalEventFavorites() {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(favoriteEventIds.value))
}

export function useEventFavorites() {
  loadLocalEventFavorites()

  const favoritesSet = computed(() => new Set(favoriteEventIds.value))

  function isFavorite(eventId: number) {
    return favoritesSet.value.has(eventId)
  }

  async function syncFavoritesFromServer() {
    const token = getUserToken()
    if (!token) {
      return
    }

    favoriteEventIds.value = await getFavoriteEventIds(token)
    persistLocalEventFavorites()
  }

  async function toggleFavorite(eventId: number) {
    const token = getUserToken()
    const nextFavorited = !favoritesSet.value.has(eventId)

    favoriteEventIds.value = nextFavorited
      ? [...favoriteEventIds.value, eventId]
      : favoriteEventIds.value.filter((item) => item !== eventId)
    persistLocalEventFavorites()

    if (!token) {
      return
    }

    try {
      if (nextFavorited) {
        await addFavoriteEvent(token, eventId)
      } else {
        await removeFavoriteEvent(token, eventId)
      }
    } catch (error) {
      // 服务端同步失败时回滚本地状态，避免界面显示与账号数据不一致。
      favoriteEventIds.value = nextFavorited
        ? favoriteEventIds.value.filter((item) => item !== eventId)
        : [...favoriteEventIds.value, eventId]
      persistLocalEventFavorites()
      throw error
    }
  }

  return {
    favoriteEventIds,
    favoritesSet,
    favoritesCount: computed(() => favoriteEventIds.value.length),
    isFavorite,
    syncFavoritesFromServer,
    toggleFavorite,
  }
}
