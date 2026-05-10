import { apiClient } from './client'
import type { ProviderItem, TranslateResponse } from '@/types'

export const translateApi = {
  async translate(
    text: string,
    sourceLang: string,
    targetLang: string,
    providerCode: string,
  ): Promise<TranslateResponse> {
    const { data } = await apiClient.post<TranslateResponse>('/translate', {
      source_text: text,
      source_lang: sourceLang,
      target_lang: targetLang,
      provider_code: providerCode,
    })
    return data
  },

  async getProviders(
    sourceLang: string,
    targetLang: string,
  ): Promise<ProviderItem[]> {
    const { data } = await apiClient.get<ProviderItem[]>(
      '/translate/providers',
      { params: { source_lang: sourceLang, target_lang: targetLang } },
    )
    return data
  },
}
