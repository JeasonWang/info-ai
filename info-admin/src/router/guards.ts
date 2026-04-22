import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { adminTokenStorage } from '@/stores/authStore'

export function requireAdminAuth(to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) {
  const needsAuth = Boolean(to.meta.requiresAuth)
  const hasToken = Boolean(adminTokenStorage.get())

  if (needsAuth && !hasToken) {
    next({ name: 'login', query: { redirect: to.fullPath || to.path } })
    return
  }

  if (to.name === 'login' && hasToken) {
    next({ name: 'dashboard' })
    return
  }

  next()
}
