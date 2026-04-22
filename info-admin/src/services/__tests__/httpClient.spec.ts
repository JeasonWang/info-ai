import { afterEach, describe, expect, it, vi } from 'vitest'
import { adminTokenStorage } from '@/stores/authStore'
import { apiRequest } from '@/services/httpClient'

describe('httpClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
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
      'http://localhost:8080/api/admin/overview',
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
})
