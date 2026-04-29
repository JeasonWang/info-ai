import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  archiveDuplicateTitles,
  archiveLowQualityInfos,
  batchRetryDetailJobs,
  batchCancelDetailJobs,
  cancelDetailJob,
  createChannel,
  getAdminOverview,
  getAuditLogs,
  getChannelHealth,
  getDetailJob,
  getDetailJobReport,
  getLowQualityInfos,
  rebuildEvents,
  retryDetailJob,
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

    await getDetailJobReport({ limit: 7, channelCode: '36kr', failureReason: 'empty_content' })
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/detail-jobs?limit=7&channel_code=36kr&failure_reason=empty_content',
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

    await batchRetryDetailJobs({ channelCode: '36kr', failureReason: 'empty_content', limit: 20 })
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/detail-jobs/retry?limit=20&channel_code=36kr&failure_reason=empty_content',
      expect.objectContaining({ method: 'POST' }),
    )

    await batchCancelDetailJobs({ channelCode: '36kr', failureReason: 'empty_content', limit: 20 })
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/detail-jobs/cancel?limit=20&channel_code=36kr&failure_reason=empty_content',
      expect.objectContaining({ method: 'POST' }),
    )

    await getDetailJob(11)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/detail-jobs/11',
      expect.any(Object),
    )

    await retryDetailJob(11)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/detail-jobs/11/retry',
      expect.objectContaining({ method: 'POST' }),
    )

    await cancelDetailJob(11)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/admin/detail-jobs/11/cancel',
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

  it('sends Max schedule fields when creating a channel', async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(JSON.stringify({ code: 0, message: 'success', data: { id: 1 } }))
    })
    vi.stubGlobal('fetch', fetchMock)

    await createChannel({
      name: '微博',
      code: 'weibo',
      base_url: 'https://weibo.com',
      category_id: 1,
      crawl_interval: 30,
      base_interval_minutes: 30,
      hot_interval_minutes: 5,
      min_interval_minutes: 3,
      max_interval_minutes: 120,
      manual_interval_enabled: 1,
      effective_interval_minutes: 5,
      is_active: 1,
    })

    const [, init] = fetchMock.mock.calls.at(0) as unknown as [RequestInfo, RequestInit]
    expect(JSON.parse(init.body as string)).toMatchObject({
      base_interval_minutes: 30,
      hot_interval_minutes: 5,
      min_interval_minutes: 3,
      max_interval_minutes: 120,
      manual_interval_enabled: 1,
      effective_interval_minutes: 5,
    })
  })
})
