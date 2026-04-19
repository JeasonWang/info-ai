import type {
  ApiResponse,
  Category,
  CategoryPayload,
  Channel,
  ChannelPayload,
  CrawlTriggerResult,
  InfoItem,
  InfoPage,
  ListInfoParams,
  StatsData,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      query.set(key, String(value))
    }
  })

  const queryString = query.toString()
  return queryString ? `?${queryString}` : ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

export async function getCategories() {
  const response = await request<ApiResponse<Category[]>>('/api/categories')
  return response.data
}

export async function getChannels(categoryId?: number) {
  const query = buildQuery({ category_id: categoryId })
  const response = await request<ApiResponse<Channel[]>>(`/api/channels${query}`)
  return response.data
}

export async function getAdminCategories() {
  const response = await request<ApiResponse<Category[]>>('/api/admin/categories')
  return response.data
}

export async function createCategory(payload: CategoryPayload) {
  const response = await request<ApiResponse<Category>>('/api/admin/categories', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return response.data
}

export async function updateCategory(id: number, payload: CategoryPayload) {
  const response = await request<ApiResponse<Category>>(`/api/admin/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
  return response.data
}

export async function getAdminChannels() {
  const response = await request<ApiResponse<Channel[]>>('/api/admin/channels')
  return response.data
}

export async function createChannel(payload: ChannelPayload) {
  const response = await request<ApiResponse<Channel>>('/api/admin/channels', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return response.data
}

export async function updateChannel(id: number, payload: ChannelPayload) {
  const response = await request<ApiResponse<Channel>>(`/api/admin/channels/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
  return response.data
}

export async function getInfos(params: ListInfoParams) {
  const query = buildQuery({
    category_id: params.category_id,
    channel_id: params.channel_id,
    keyword: params.keyword,
    page: params.page,
    page_size: params.page_size,
  })
  const response = await request<ApiResponse<InfoPage>>(`/api/infos${query}`)
  return response.data
}

export async function getInfoById(id: number) {
  const response = await request<ApiResponse<InfoItem>>(`/api/infos/${id}`)
  return response.data
}

export async function getStats() {
  const response = await request<ApiResponse<StatsData>>('/api/stats')
  return response.data
}

export async function triggerCrawl(channelCode: string) {
  const query = buildQuery({ channel_code: channelCode })
  const response = await request<ApiResponse<CrawlTriggerResult>>(
    `/api/crawl/trigger${query}`,
    {
      method: 'POST',
    },
  )
  return response.data
}
