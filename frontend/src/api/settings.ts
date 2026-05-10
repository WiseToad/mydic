import { apiClient } from './client'
import type { UserSettings } from '@/types'

export const settingsApi = {
  async getSettings(): Promise<UserSettings> {
    const { data } = await apiClient.get<UserSettings>('/settings')
    return data
  },

  async saveSettings(settings: UserSettings): Promise<UserSettings> {
    const { data } = await apiClient.put<UserSettings>('/settings', settings)
    return data
  },
}
