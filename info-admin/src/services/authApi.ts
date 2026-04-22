import { apiRequest } from '@/services/httpClient'
import type { LoginResult } from '@/types/auth'

export function loginAdmin(email: string, password: string) {
  return apiRequest<LoginResult>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}
