import { computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { post, get } from '@/services/request'
import type { LoginResult, PublicUser } from '@/types'

export function useAuth() {
  const store = useUserStore()

  const isLoggedIn = computed(() => store.isLoggedIn)
  const user = computed(() => store.user)

  async function login(email: string, password: string): Promise<void> {
    const result = await post<LoginResult>('/auth/login', { email, password }, true)
    store.setAuth(result.token, result.user)
  }

  async function register(email: string, password: string): Promise<void> {
    const result = await post<LoginResult>('/auth/register', { email, password }, true)
    store.setAuth(result.token, result.user)
  }

  async function fetchUser(): Promise<void> {
    if (!store.token) return
    try {
      const result = await get<PublicUser>('/me')
      store.user = result
    } catch {
      store.clearAuth()
    }
  }

  function logout(): void {
    store.clearAuth()
    uni.reLaunch({ url: '/pages/login/login' })
  }

  return {
    isLoggedIn,
    user,
    login,
    register,
    fetchUser,
    logout,
  }
}
