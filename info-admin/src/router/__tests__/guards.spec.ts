import { describe, expect, it, vi } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'
import { requireAdminAuth } from '@/router/guards'
import { adminTokenStorage } from '@/stores/authStore'

function route(path: string, requiresAuth = false) {
  return {
    path,
    fullPath: path,
    name: undefined,
    matched: [],
    query: {},
    params: {},
    hash: '',
    redirectedFrom: undefined,
    meta: { requiresAuth },
  } as unknown as RouteLocationNormalized
}

describe('router guards', () => {
  it('redirects anonymous users to login when route requires admin auth', () => {
    window.localStorage.clear()
    const next = vi.fn()

    requireAdminAuth(route('/dashboard', true), route('/login'), next)

    expect(next).toHaveBeenCalledWith({ name: 'login', query: { redirect: '/dashboard' } })
  })

  it('allows authenticated admins to enter protected routes', () => {
    adminTokenStorage.set('admin-token')
    const next = vi.fn()

    requireAdminAuth(route('/dashboard', true), route('/login'), next)

    expect(next).toHaveBeenCalledWith()
  })
})
