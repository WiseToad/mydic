import { apiClient } from './client'
import type { Definition, ProviderItem } from '@/types'

export const definitionApi = {
  async get(word: string, lang: string, providerCode: string): Promise<Definition | null> {
    try {
      const { data } = await apiClient.get<Definition>('/definition', {
        params: { word, lang, provider_code: providerCode },
      })
      return data
    } catch (e: unknown) {
      if ((e as { response?: { status?: number } }).response?.status === 404) return null
      throw e
    }
  },

  async providers(lang: string): Promise<ProviderItem[]> {
    const { data } = await apiClient.get<ProviderItem[]>('/definition/providers', {
      params: { lang },
    })
    return data
  },
}
