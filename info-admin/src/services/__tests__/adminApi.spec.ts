import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  archiveDuplicateTitles,
  archiveLowQualityInfos,
  getAdminOverview,
  getAuditLogs,
  getChannelHealth,
  getLowQualityInfos,
  rebuildEvents,
  refreshQuality,
  retryLowQualityDetails,
  triggerCrawlTask,
} from '@/services/adminApi'
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

    await getChannelHealth()
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/channel-health',
      expect.any(Object),
    )

    await getLowQualityInfos(12)

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/low-quality-infos?limit=12',
      expect.any(Object),
    )

    await triggerCrawlTask('weibo')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/crawl-tasks/weibo/trigger',
      expect.objectContaining({ method: 'POST' }),
    )

    await rebuildEvents()
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/rebuild-events',
      expect.objectContaining({ method: 'POST' }),
    )

    await refreshQuality()
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/refresh-quality',
      expect.objectContaining({ method: 'POST' }),
    )

    await retryLowQualityDetails(15)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/retry-low-quality-details?limit=15',
      expect.objectContaining({ method: 'POST' }),
    )

    await archiveLowQualityInfos()
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/archive-low-quality',
      expect.objectContaining({ method: 'POST' }),
    )

    await archiveDuplicateTitles()
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/archive-duplicate-titles',
      expect.objectContaining({ method: 'POST' }),
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
