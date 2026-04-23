import { apiRequest } from '@/services/httpClient'
import { apiV1 } from '@/services/apiPath'
import type {
  AdminCategory,
  AdminChannel,
  AdminOverview,
  CategoryPayload,
  ChannelPayload,
  CrawlRunSummary,
  CrawlTask,
  QualitySnapshot,
} from '@/types/admin'

export function getAdminOverview() {
  return apiRequest<AdminOverview>(apiV1('/admin/overview'))
}

export function getCrawlRuns(limit = 20) {
  return apiRequest<CrawlRunSummary[]>(apiV1(`/admin/crawl-runs?limit=${limit}`))
}

export function getQualitySnapshots(limit = 20) {
  return apiRequest<QualitySnapshot[]>(apiV1(`/admin/quality-snapshots?limit=${limit}`))
}

export function getCrawlTasks() {
  return apiRequest<CrawlTask[]>(apiV1('/admin/crawl-tasks'))
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
