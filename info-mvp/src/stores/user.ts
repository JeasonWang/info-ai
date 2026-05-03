import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PublicUser } from '@/types'
import { getToken, setToken, removeToken } from '@/utils/storage'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(getToken())
  const user = ref<PublicUser | null>(null)
  const isLoggedIn = computed(() => !!token.value && !!user.value)

  function setAuth(newToken: string, newUser: PublicUser) {
    token.value = newToken
    user.value = newUser
    setToken(newToken)
  }

  function clearAuth() {
    token.value = ''
    user.value = null
    removeToken()
  }

  return {
    token,
    user,
    isLoggedIn,
    setAuth,
    clearAuth,
  }
})
