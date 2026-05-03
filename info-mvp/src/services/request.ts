import type { ApiResponse } from '@/types'
import { getToken, removeToken } from '@/utils/storage'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const API_PREFIX = '/v1'

interface RequestConfig {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  headers?: Record<string, string>
  noAuth?: boolean
}

let isReLaunchingToLogin = false

function showError(message: string) {
  uni.showToast({ title: message, icon: 'none' })
}

function handleUnauthorized() {
  removeToken()
  if (isReLaunchingToLogin) return
  isReLaunchingToLogin = true
  // 只在用户曾经登录过（本地有缓存的用户信息）时才提示“过期”
  // 从未登录的用户遇到 401，静默清理状态即可
  showError('登录已过期，请重新登录')
  uni.reLaunch({
    url: '/pages/login/login',
    complete: () => {
      setTimeout(() => {
        isReLaunchingToLogin = false
      }, 1000)
    },
  })
}

function isNeverLoggedIn(): boolean {
  return !getToken()
}

export function request<T>(config: RequestConfig): Promise<T> {
  return new Promise((resolve, reject) => {
    const token = getToken()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...config.headers,
    }

    if (token && !config.noAuth) {
      headers.Authorization = `Bearer ${token}`
    }

    uni.request({
      url: `${BASE_URL}${API_PREFIX}${config.url}`,
      method: config.method || 'GET',
      data: config.data,
      header: headers,
      success: (res) => {
        if (res.statusCode === 401) {
          if (isNeverLoggedIn()) {
            removeToken()
            reject(new Error('Unauthorized'))
            return
          }
          handleUnauthorized()
          reject(new Error('Unauthorized'))
          return
        }

        if (res.statusCode >= 200 && res.statusCode < 300) {
          const result = res.data as ApiResponse<T>
          if (result.code !== 0 && result.code !== 200) {
            showError(result.message || '请求失败')
            reject(new Error(result.message))
            return
          }
          resolve(result.data)
        } else {
          const msg = (res.data as ApiResponse<unknown>)?.message || `请求失败: ${res.statusCode}`
          showError(msg)
          reject(new Error(msg))
        }
      },
      fail: (err) => {
        showError('网络错误，请检查网络连接')
        reject(err)
      },
    })
  })
}

export function get<T>(url: string, noAuth?: boolean): Promise<T> {
  return request<T>({ url, method: 'GET', noAuth })
}

export function post<T>(url: string, data?: unknown, noAuth?: boolean): Promise<T> {
  return request<T>({ url, method: 'POST', data, noAuth })
}

export function put<T>(url: string, data?: unknown): Promise<T> {
  return request<T>({ url, method: 'PUT', data })
}

export function del<T>(url: string): Promise<T> {
  return request<T>({ url, method: 'DELETE' })
}
