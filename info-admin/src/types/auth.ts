export interface AdminUser {
  id: number
  email: string
  role: string
}

export interface LoginResult {
  token: string
  user: AdminUser
}
