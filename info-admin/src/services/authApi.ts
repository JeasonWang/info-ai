import { apiV1 } from '@/services/apiPath'
import { apiRequest } from '@/services/httpClient'
import type { LoginResult } from '@/types/auth'

export function loginAdmin(email: string, password: string) {
  return apiRequest<LoginResult>(apiV1('/auth/login'), {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}
