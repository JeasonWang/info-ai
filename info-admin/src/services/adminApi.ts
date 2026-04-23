import { apiRequest } from '@/services/httpClient'
import { apiV1 } from '@/services/apiPath'
import type {
  AdminCategory,
  AdminChannel,
  AdminOverview,
  AdminActionResult,
  ChannelHealth,
  AuditLog,
  CategoryPayload,
  ChannelPayload,
  CrawlRunSummary,
  CrawlTask,
  LowQualityInfo,
  QualitySnapshot,
} from '@/types/admin'

export function getAdminOverview() {
  return apiRequest<AdminOverview>(apiV1('/admin/overview'))
}

export function getCrawlRuns(limit = 20) {
  return apiRequest<CrawlRunSummary[]>(apiV1(`/admin/crawl-runs?limit=${limit}`))
}

export function getChannelHealth() {
  return apiRequest<ChannelHealth[]>(apiV1('/admin/channel-health'))
}

export function getQualitySnapshots(limit = 20) {
  return apiRequest<QualitySnapshot[]>(apiV1(`/admin/quality-snapshots?limit=${limit}`))
}

export function getLowQualityInfos(limit = 20) {
  return apiRequest<LowQualityInfo[]>(apiV1(`/admin/low-quality-infos?limit=${limit}`))
}

export function getCrawlTasks() {
  return apiRequest<CrawlTask[]>(apiV1('/admin/crawl-tasks'))
}

export function getAuditLogs(limit = 30) {
  return apiRequest<AuditLog[]>(apiV1(`/admin/audit-logs?limit=${limit}`))
}

export function getCategories() {
  return apiRequest<AdminCategory[]>(apiV1('/admin/categories'))
}

export function createCategory(payload: CategoryPayload) {
  return apiRequest<AdminCategory>(apiV1('/admin/categories'), {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateCategory(id: number, payload: CategoryPayload) {
  return apiRequest<AdminCategory>(apiV1(`/admin/categories/${id}`), {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function getChannels() {
  return apiRequest<AdminChannel[]>(apiV1('/admin/channels'))
}

export function createChannel(payload: ChannelPayload) {
  return apiRequest<AdminChannel>(apiV1('/admin/channels'), {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateChannel(id: number, payload: ChannelPayload) {
  return apiRequest<AdminChannel>(apiV1(`/admin/channels/${id}`), {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function triggerCrawlTask(channelCode: string) {
  return apiRequest<AdminActionResult>(apiV1(`/admin/crawl-tasks/${encodeURIComponent(channelCode)}/trigger`), {
    method: 'POST',
  })
}

export function rebuildEvents() {
  return apiRequest<AdminActionResult>(apiV1('/admin/rebuild-events'), {
    method: 'POST',
  })
}

export function refreshQuality() {
  return apiRequest<AdminActionResult>(apiV1('/admin/refresh-quality'), {
    method: 'POST',
  })
}

export function archiveLowQualityInfos() {
  return apiRequest<AdminActionResult>(apiV1('/admin/archive-low-quality'), {
    method: 'POST',
  })
}

export function archiveDuplicateTitles() {
  return apiRequest<AdminActionResult>(apiV1('/admin/archive-duplicate-titles'), {
    method: 'POST',
  })
}
