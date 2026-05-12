import { apiRequest } from '@/services/httpClient'
import { apiV1 } from '@/services/apiPath'
import type {
  AdminCategory,
  AdminChannel,
  AdminOverview,
  AdminActionResult,
  ChannelHealth,
  ChannelQualityReport,
  AuditLog,
  CategoryPayload,
  ChannelPayload,
  CrawlRunSummary,
  CrawlTask,
  DetailJobDetail,
  DetailJobReport,
  EventAnalysisQualityReport,
  LLMModelConfig,
  LLMModelConfigPayload,
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

export function getChannelQualityReport(sampleLimit = 5) {
  return apiRequest<ChannelQualityReport>(apiV1(`/admin/channel-quality-report?sample_limit=${sampleLimit}`))
}

export function getEventAnalysisQualityReport(limit = 20) {
  return apiRequest<EventAnalysisQualityReport>(apiV1(`/admin/event-analysis-quality-report?limit=${limit}`))
}

export function getQualitySnapshots(limit = 20) {
  return apiRequest<QualitySnapshot[]>(apiV1(`/admin/quality-snapshots?limit=${limit}`))
}

export function getLowQualityInfos(limit = 20) {
  return apiRequest<LowQualityInfo[]>(apiV1(`/admin/low-quality-infos?limit=${limit}`))
}

interface DetailJobQuery {
  limit?: number
  channelCode?: string
  failureReason?: string
}

function detailJobQuery(params: DetailJobQuery = {}) {
  const query = new URLSearchParams()
  query.set('limit', String(params.limit ?? 10))
  if (params.channelCode) query.set('channel_code', params.channelCode)
  if (params.failureReason) query.set('failure_reason', params.failureReason)
  return query.toString()
}

export function getDetailJobReport(params: DetailJobQuery | number = {}) {
  const query = typeof params === 'number' ? detailJobQuery({ limit: params }) : detailJobQuery(params)
  return apiRequest<DetailJobReport>(apiV1(`/admin/detail-jobs?${query}`))
}

export function getDetailJob(id: number) {
  return apiRequest<DetailJobDetail>(apiV1(`/admin/detail-jobs/${id}`))
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

export function getLLMModelConfigs() {
  return apiRequest<LLMModelConfig[]>(apiV1('/admin/llm-model-configs'))
}

export function createLLMModelConfig(payload: LLMModelConfigPayload) {
  return apiRequest<LLMModelConfig>(apiV1('/admin/llm-model-configs'), {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateLLMModelConfig(id: number, payload: LLMModelConfigPayload) {
  return apiRequest<LLMModelConfig>(apiV1(`/admin/llm-model-configs/${id}`), {
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

export function retryLowQualityDetails(limit = 20) {
  return apiRequest<AdminActionResult>(apiV1(`/admin/retry-low-quality-details?limit=${limit}`), {
    method: 'POST',
  })
}

export function enqueueEventAnalysisDetailJobs(limit = 20) {
  return apiRequest<AdminActionResult>(apiV1(`/admin/event-analysis-detail-jobs?limit=${limit}`), {
    method: 'POST',
  })
}

export function rebuildStaleEventAnalysis(limit = 200) {
  return apiRequest<AdminActionResult>(apiV1(`/admin/rebuild-stale-event-analysis?limit=${limit}`), {
    method: 'POST',
  })
}

export function retryDetailJob(id: number) {
  return apiRequest<AdminActionResult>(apiV1(`/admin/detail-jobs/${id}/retry`), {
    method: 'POST',
  })
}

export function batchRetryDetailJobs(params: DetailJobQuery = {}) {
  return apiRequest<AdminActionResult>(apiV1(`/admin/detail-jobs/retry?${detailJobQuery(params)}`), {
    method: 'POST',
  })
}

export function batchCancelDetailJobs(params: DetailJobQuery = {}) {
  return apiRequest<AdminActionResult>(apiV1(`/admin/detail-jobs/cancel?${detailJobQuery(params)}`), {
    method: 'POST',
  })
}

export function cancelDetailJob(id: number) {
  return apiRequest<AdminActionResult>(apiV1(`/admin/detail-jobs/${id}/cancel`), {
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

export interface ChannelCredentialInfo {
  channel_code: string
  cookie_configured: boolean
  cookie_preview: string
  cookie_status: string
  extra_credentials: Record<string, any>
  updated_at: string | null
  updated_by: string
}

export interface CredentialTestResult {
  channel_code: string
  success: boolean
  response_code: number
}

export interface ChannelCredentialPayload {
  cookies: string
  extra_credentials?: Record<string, any>
  updated_by?: string
}

export function getChannelCredentials(channelCode: string) {
  return apiRequest<ChannelCredentialInfo>(apiV1(`/admin/channels/${encodeURIComponent(channelCode)}/credentials`))
}

export function updateChannelCredentials(channelCode: string, payload: ChannelCredentialPayload) {
  return apiRequest<{ channel_code: string }>(apiV1(`/admin/channels/${encodeURIComponent(channelCode)}/credentials`), {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function testChannelCredentials(channelCode: string) {
  return apiRequest<CredentialTestResult>(apiV1(`/admin/channels/${encodeURIComponent(channelCode)}/credentials/test`), {
    method: 'POST',
  })
}

export function deleteChannelCredentials(channelCode: string) {
  return apiRequest<{ channel_code: string }>(apiV1(`/admin/channels/${encodeURIComponent(channelCode)}/credentials`), {
    method: 'DELETE',
  })
}

export interface EventAnalysisRun {
  run_id: number
  analysis_version: string
  mode: string
  provider: string
  model_name: string
  status: string
  input_item_count: number
  quality_score: number
  confidence: number
  fallback_used: boolean
  failure_reason: string
  started_at: string
  finished_at: string
  created_at: string
}

export interface EventAnalysisSource {
  source_id: number
  info_id: number
  title: string
  role: string
  weight: number
  quality_score: number
  channel_name: string
  source_url: string
  event_time: string
}

export interface EventAnalysisRunsResult {
  event_id: number
  event_title: string
  runs: EventAnalysisRun[]
}

export interface EventAnalysisSourcesResult {
  event_id: number
  event_title: string
  run: EventAnalysisRun
  sources: EventAnalysisSource[]
}

export function getEventAnalysisRuns(eventId: number) {
  return apiRequest<EventAnalysisRunsResult>(apiV1(`/admin/events/${eventId}/analysis-runs`))
}

export function getEventAnalysisSources(eventId: number, runId: number) {
  return apiRequest<EventAnalysisSourcesResult>(apiV1(`/admin/events/${eventId}/analysis-sources?run_id=${runId}`))
}
