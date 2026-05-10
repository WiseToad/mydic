import { apiClient } from './client'
import type { ProviderItem } from '@/types'

export const lexicalApi = {
  async matches(
    word: string,
    sourceLang: string,
    targetLang: string,
    providerCode: string,
  ): Promise<string[]> {
    const { data } = await apiClient.get<{ matches: string[] }>('/lexical', {
      params: {
        word,
        source_lang: sourceLang,
        target_lang: targetLang,
        provider_code: providerCode,
      },
    })
    return data.matches
  },

  async providers(sourceLang: string, targetLang: string): Promise<ProviderItem[]> {
    const { data } = await apiClient.get<ProviderItem[]>('/lexical/providers', {
      params: { source_lang: sourceLang, target_lang: targetLang },
    })
    return data
  },
}
