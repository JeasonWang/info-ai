import { afterEach, describe, expect, it, vi } from 'vitest'
import { adminTokenStorage } from '@/stores/authStore'
import { apiRequest } from '@/services/httpClient'

describe('httpClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
    vi.resetModules()
    window.localStorage.clear()
  })

  it('injects admin token and unwraps response data', async () => {
    adminTokenStorage.set('admin-token')
    const fetchMock = vi.fn(async () => {
      return new Response(JSON.stringify({ code: 0, message: 'success', data: { ok: true } }))
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiRequest<{ ok: boolean }>('/api/admin/overview')

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/admin/overview',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer admin-token',
          'Content-Type': 'application/json',
        }),
      }),
    )
  })

  it('clears token when admin API returns unauthorized', async () => {
    adminTokenStorage.set('expired-token')
    vi.stubGlobal('fetch', vi.fn(async () => {
      return new Response(JSON.stringify({ code: 401, message: '未登录' }), { status: 401 })
    }))

    await expect(apiRequest('/api/admin/overview')).rejects.toThrow('未登录')
    expect(adminTokenStorage.get()).toBe('')
  })

  it('does not duplicate /api when VITE_API_BASE_URL is /api', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api')
    const { apiRequest } = await import('@/services/httpClient')
    const fetchMock = vi.fn(async () => {
      return new Response(JSON.stringify({ code: 0, message: 'success', data: { ok: true } }))
    })
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest<{ ok: boolean }>('/api/v1/admin/overview')

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/admin/overview', expect.any(Object))
  })
})
