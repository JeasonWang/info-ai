import type { PublicUser } from '@/types'

const TOKEN_KEY = 'info-max-token'
const USER_KEY = 'info-max-user'
export const USER_SESSION_CHANGED = 'info-max-user-session-changed'

export function getUserToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getSavedUser(): PublicUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as PublicUser
  } catch {
    clearUserSession()
    return null
  }
}

export function saveUserSession(token: string, user: PublicUser) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  window.dispatchEvent(new Event(USER_SESSION_CHANGED))
}

export function clearUserSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  window.dispatchEvent(new Event(USER_SESSION_CHANGED))
}
