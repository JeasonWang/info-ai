import type { AdminUser } from '@/types/auth'

const TOKEN_KEY = 'info-admin-token'
const USER_KEY = 'info-admin-user'

export const adminTokenStorage = {
  get() {
    return window.localStorage.getItem(TOKEN_KEY) ?? ''
  },
  set(token: string) {
    window.localStorage.setItem(TOKEN_KEY, token)
  },
  clear() {
    window.localStorage.removeItem(TOKEN_KEY)
  },
}

export const adminUserStorage = {
  get(): AdminUser | null {
    const raw = window.localStorage.getItem(USER_KEY)
    if (!raw) {
      return null
    }
    try {
      return JSON.parse(raw) as AdminUser
    } catch {
      window.localStorage.removeItem(USER_KEY)
      return null
    }
  },
  set(user: AdminUser) {
    window.localStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  clear() {
    window.localStorage.removeItem(USER_KEY)
  },
}

export function clearAdminSession() {
  adminTokenStorage.clear()
  adminUserStorage.clear()
}
