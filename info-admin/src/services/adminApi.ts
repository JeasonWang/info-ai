import { apiRequest } from '@/services/httpClient'
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
  return apiRequest<AdminOverview>('/api/admin/overview')
}

export function getCrawlRuns(limit = 20) {
  return apiRequest<CrawlRunSummary[]>(`/api/admin/crawl-runs?limit=${limit}`)
}

export function getQualitySnapshots(limit = 20) {
  return apiRequest<QualitySnapshot[]>(`/api/admin/quality-snapshots?limit=${limit}`)
}

export function getCrawlTasks() {
  return apiRequest<CrawlTask[]>('/api/admin/crawl-tasks')
}

export function getCategories() {
  return apiRequest<AdminCategory[]>('/api/admin/categories')
}

export function createCategory(payload: CategoryPayload) {
  return apiRequest<AdminCategory>('/api/admin/categories', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateCategory(id: number, payload: CategoryPayload) {
  return apiRequest<AdminCategory>(`/api/admin/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function getChannels() {
  return apiRequest<AdminChannel[]>('/api/admin/channels')
}

export function createChannel(payload: ChannelPayload) {
  return apiRequest<AdminChannel>('/api/admin/channels', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateChannel(id: number, payload: ChannelPayload) {
  return apiRequest<AdminChannel>(`/api/admin/channels/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
