import { clearAdminSession, adminTokenStorage } from '@/stores/authStore'
import { ApiError, type ApiResponse } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_INFO_SERVE_BASE_URL || 'http://localhost:8080'

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = adminTokenStorage.get()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  })

  const result = await readResponse<T>(response)
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearAdminSession()
    }
    throw new ApiError(result.message || `请求失败：${response.status}`, response.status)
  }

  return result.data
}

async function readResponse<T>(response: Response): Promise<ApiResponse<T>> {
  try {
    return (await response.json()) as ApiResponse<T>
  } catch {
    return {
      code: response.status,
      message: '服务返回了无法解析的数据',
      data: undefined as T,
    }
  }
}
