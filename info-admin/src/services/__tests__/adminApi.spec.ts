import { afterEach, describe, expect, it, vi } from 'vitest'
import { getAdminOverview, getAuditLogs } from '@/services/adminApi'
import { loginAdmin } from '@/services/authApi'

describe('admin API versioned paths', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses /api/v1 for admin business APIs', async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(JSON.stringify({ code: 0, message: 'success', data: { event_count: 1 } }))
    })
    vi.stubGlobal('fetch', fetchMock)

    await getAdminOverview()

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/overview',
      expect.any(Object),
    )

    await getAuditLogs(10)

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/audit-logs?limit=10',
      expect.any(Object),
    )
  })

  it('uses /api/v1 for admin login', async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(JSON.stringify({ code: 0, message: 'success', data: { token: 'token' } }))
    })
    vi.stubGlobal('fetch', fetchMock)

    await loginAdmin('admin@example.com', 'Admin123456')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/auth/login',
      expect.objectContaining({
        method: 'POST',
      }),
    )
  })
})
