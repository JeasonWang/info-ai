const API_VERSION_PREFIX = '/api/v1'

// 统一管理 info-serve 版本化路径，避免业务接口里散落硬编码前缀。
export function apiV1(path: string) {
  return `${API_VERSION_PREFIX}${path}`
}
