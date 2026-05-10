import { apiClient } from './client'
import type { ContextExample, Definition, ProviderItem } from '@/types'

export const dictionaryApi = {
  async definition(word: string, lang: string, providerCode: string): Promise<Definition | null> {
    try {
      const { data } = await apiClient.get<Definition>('/dictionary/definition', {
        params: { word, lang, provider_code: providerCode },
      })
      return data
    } catch (e: unknown) {
      if ((e as { response?: { status?: number } }).response?.status === 404) return null
      throw e
    }
  },

  async contextExamples(
    text: string,
    sourceLang: string,
    targetLang: string,
    providerCode: string,
  ): Promise<ContextExample[]> {
    const { data } = await apiClient.get<{ examples: ContextExample[] }>('/dictionary/context', {
      params: {
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
        provider_code: providerCode,
      },
    })
    return data.examples
  },

  async definitionProviders(lang: string): Promise<ProviderItem[]> {
    const { data } = await apiClient.get<ProviderItem[]>('/dictionary/definition/providers', {
      params: { lang },
    })
    return data
  },

  async contextProviders(sourceLang: string, targetLang: string): Promise<ProviderItem[]> {
    const { data } = await apiClient.get<ProviderItem[]>('/dictionary/context/providers', {
      params: { source_lang: sourceLang, target_lang: targetLang },
    })
    return data
  },
}
