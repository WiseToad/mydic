import { apiClient } from './client'
import type {
  WordbookEntry,
  WordbookEntryCreate,
  WordbookEntryUpdate,
  WordbookListResponse,
  WordbookLookupResult,
  WordbookMoveItem,
  WordbookSearchResponse,
  WordGroup,
  WordGroupCount,
  WordGroupUpdate,
} from '@/types'

export const wordbookApi = {
  async list(groupId: number, langPairs?: string[]): Promise<WordbookListResponse> {
    const params = new URLSearchParams()
    params.set('group_id', String(groupId))
    if (langPairs && langPairs.length > 0) {
      for (const p of langPairs) params.append('lang_pair', p)
    }
    const { data } = await apiClient.get<WordbookListResponse>('/wordbook', { params })
    return data
  },

  async create(entry: WordbookEntryCreate, groupId?: number): Promise<WordbookEntry> {
    const { data } = await apiClient.post<WordbookEntry>('/wordbook', {
      ...entry,
      ...(groupId !== undefined ? { group_id: groupId } : {}),
    })
    return data
  },

  async update(id: number, update: WordbookEntryUpdate): Promise<WordbookEntry> {
    const { data } = await apiClient.patch<WordbookEntry>(`/wordbook/${id}`, update)
    return data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/wordbook/${id}`)
  },

  async reorder(body: WordbookMoveItem): Promise<void> {
    await apiClient.put('/wordbook/reorder', body)
  },

  async reorderGroups(body: WordbookMoveItem): Promise<void> {
    await apiClient.put('/wordbook/groups/reorder', body)
  },

  async listLangPairs(): Promise<string[]> {
    const { data } = await apiClient.get<string[]>('/wordbook/lang-pairs')
    return data
  },

  async search(
    q: string,
    searchIn: 'source_text' | 'target_text' | 'notes',
    langPairs: string[],
    colors: string[],
    relaxedFilters: Array<'lang_pairs' | 'colors'> = [],
    searchLimit?: number,
  ): Promise<WordbookSearchResponse> {
    const params = new URLSearchParams()
    params.set('q', q)
    params.set('search_in', searchIn)
    for (const p of langPairs) params.append('lang_pairs', p)
    for (const c of colors) params.append('colors', c)
    for (const f of relaxedFilters) params.append('relaxed_filters', f)
    if (searchLimit !== undefined) params.set('search_limit', String(searchLimit))
    const { data } = await apiClient.get<WordbookSearchResponse>('/wordbook/search', { params })
    return data
  },

  /** Returns the entry's id/group_id/color, or null if not in wordbook (204). */
  async lookup(sourceLang: string, targetLang: string, sourceText: string): Promise<WordbookLookupResult | null> {
    const response = await apiClient.get<WordbookLookupResult | null>('/wordbook/lookup', {
      params: { source_lang: sourceLang, target_lang: targetLang, source_text: sourceText },
    })
    return response.status === 204 ? null : response.data
  },

  // ── Word groups ────────────────────────────────────────────────────────────

  async listGroups(langPairs?: string[]): Promise<WordGroup[]> {
    const params = new URLSearchParams()
    if (langPairs && langPairs.length > 0) {
      for (const p of langPairs) params.append('lang_pair', p)
    }
    const { data } = await apiClient.get<WordGroup[]>('/wordbook/groups', { params })
    return data
  },

  async listGroupCounts(langPairs?: string[], colors?: string[]): Promise<WordGroupCount[]> {
    const params = new URLSearchParams()
    if (langPairs && langPairs.length > 0) {
      for (const p of langPairs) params.append('lang_pair', p)
    }
    if (colors && colors.length > 0) {
      for (const c of colors) params.append('colors', c)
    }
    const { data } = await apiClient.get<WordGroupCount[]>('/wordbook/groups/counts', { params })
    return data
  },

  async createGroup(name: string): Promise<WordGroup> {
    const { data } = await apiClient.post<WordGroup>('/wordbook/groups', { name })
    return data
  },

  async updateGroup(id: number, update: WordGroupUpdate): Promise<WordGroup> {
    const { data } = await apiClient.patch<WordGroup>(`/wordbook/groups/${id}`, update)
    return data
  },

  async deleteGroup(id: number): Promise<void> {
    await apiClient.delete(`/wordbook/groups/${id}`)
  },

  async setEntryGroup(entryId: number, groupId: number): Promise<void> {
    await apiClient.put(`/wordbook/${entryId}/group/${groupId}`)
  },
}
