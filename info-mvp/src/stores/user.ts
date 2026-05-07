import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PublicUser } from '@/types'
import { getStoredUser, getToken, removeStoredUser, removeToken, setStoredUser, setToken } from '@/utils/storage'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(getToken())
  const user = ref<PublicUser | null>(getStoredUser())
  const isLoggedIn = computed(() => !!token.value && !!user.value)

  function setAuth(newToken: string, newUser: PublicUser) {
    token.value = newToken
    user.value = newUser
    setToken(newToken)
    setStoredUser(newUser)
  }

  function setUser(newUser: PublicUser) {
    user.value = newUser
    setStoredUser(newUser)
  }

  function clearAuth() {
    token.value = ''
    user.value = null
    removeToken()
    removeStoredUser()
  }

  return {
    token,
    user,
    isLoggedIn,
    setAuth,
    setUser,
    clearAuth,
  }
})
