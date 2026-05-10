import { apiClient } from './client'
import type { Token, User } from '@/types'

export const authApi = {
  async getAppConfig(): Promise<{ registration_enabled: boolean }> {
    const { data } = await apiClient.get<{ registration_enabled: boolean }>('/auth/config')
    return data
  },

  async register(username: string, password: string): Promise<User> {
    const { data } = await apiClient.post<User>('/auth/register', { username, password })
    return data
  },

  async login(username: string, password: string): Promise<Token> {
    const form = new URLSearchParams({ username, password })
    const { data } = await apiClient.post<Token>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },

  async me(): Promise<User> {
    const { data } = await apiClient.get<User>('/auth/me')
    return data
  },
}
