import type { PublicUser } from '@/types'

const TOKEN_KEY = 'info_mvp_token'
const USER_KEY = 'info_mvp_user'

export function getToken(): string {
  try {
    return uni.getStorageSync(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token: string): void {
  uni.setStorageSync(TOKEN_KEY, token)
}

export function removeToken(): void {
  uni.removeStorageSync(TOKEN_KEY)
}

export function getStoredUser(): PublicUser | null {
  try {
    const raw = uni.getStorageSync(USER_KEY)
    if (!raw) return null
    return JSON.parse(raw) as PublicUser
  } catch {
    uni.removeStorageSync(USER_KEY)
    return null
  }
}

export function setStoredUser(user: PublicUser): void {
  uni.setStorageSync(USER_KEY, JSON.stringify(user))
}

export function removeStoredUser(): void {
  uni.removeStorageSync(USER_KEY)
}
