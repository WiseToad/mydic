import { apiClient } from './client'
import type { LanguageItem } from '@/types'

export const languagesApi = {
  async getLanguages(): Promise<LanguageItem[]> {
    const { data } = await apiClient.get<{ languages: LanguageItem[] }>('/languages')
    return data.languages
  },

  async saveLanguages(languages: LanguageItem[]): Promise<LanguageItem[]> {
    const { data } = await apiClient.put<{ languages: LanguageItem[] }>('/languages', { languages })
    return data.languages
  },
}
