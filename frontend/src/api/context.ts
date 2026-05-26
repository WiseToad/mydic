import { apiClient } from './client'
import type { ContextExample, ProviderItem } from '@/types'

export const contextApi = {
  async examples(
    text: string,
    sourceLang: string,
    targetLang: string,
    providerCode: string,
  ): Promise<ContextExample[]> {
    const { data } = await apiClient.get<{ examples: ContextExample[] }>('/context', {
      params: {
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
        provider_code: providerCode,
      },
    })
    return data.examples
  },

  async providers(sourceLang: string, targetLang: string): Promise<ProviderItem[]> {
    const { data } = await apiClient.get<ProviderItem[]>('/context/providers', {
      params: { source_lang: sourceLang, target_lang: targetLang },
    })
    return data
  },
}
