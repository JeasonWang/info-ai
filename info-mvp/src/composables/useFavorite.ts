import { ref } from 'vue'
import { addFavoriteEvent, getFavoriteEventIds, removeFavoriteEvent } from '@/services/api'
import { getToken } from '@/utils/storage'

export function useFavorite(eventId: number) {
  const isFavorited = ref(false)
  const loading = ref(false)

  async function check() {
    if (!getToken()) {
      isFavorited.value = false
      return
    }
    try {
      const { event_ids } = await getFavoriteEventIds()
      isFavorited.value = event_ids.includes(eventId)
    } catch {
      isFavorited.value = false
    }
  }

  async function toggle() {
    if (loading.value) return
    loading.value = true
    try {
      if (isFavorited.value) {
        await removeFavoriteEvent(eventId)
        isFavorited.value = false
        uni.showToast({ title: '已取消收藏', icon: 'success' })
      } else {
        await addFavoriteEvent(eventId)
        isFavorited.value = true
        uni.showToast({ title: '收藏成功', icon: 'success' })
      }
    } catch {
      // handled by request interceptor
    } finally {
      loading.value = false
    }
  }

  return {
    isFavorited,
    loading,
    check,
    toggle,
  }
}
