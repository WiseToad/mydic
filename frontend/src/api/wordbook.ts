import { apiClient } from './client'
import type {
  WordbookEntry,
  WordbookEntryCreate,
  WordbookEntryUpdate,
  WordbookReorder,
  WordGroup,
  WordGroupUpdate,
} from '@/types'

export const wordbookApi = {
  async list(): Promise<WordbookEntry[]> {
    const { data } = await apiClient.get<WordbookEntry[]>('/wordbook')
    return data
  },

  async create(entry: WordbookEntryCreate): Promise<WordbookEntry> {
    const { data } = await apiClient.post<WordbookEntry>('/wordbook', entry)
    return data
  },

  async update(id: number, update: WordbookEntryUpdate): Promise<WordbookEntry> {
    const { data } = await apiClient.patch<WordbookEntry>(`/wordbook/${id}`, update)
    return data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/wordbook/${id}`)
  },

  async batchRemove(ids: number[]): Promise<void> {
    await apiClient.post('/wordbook/batch-delete', { ids })
  },

  async reorder(body: WordbookReorder): Promise<void> {
    await apiClient.put('/wordbook/reorder', body)
  },

  async reorderGroups(body: WordbookReorder): Promise<void> {
    await apiClient.put('/wordbook/groups/reorder', body)
  },

  // ── Word groups ────────────────────────────────────────────────────────────

  async listGroups(): Promise<WordGroup[]> {
    const { data } = await apiClient.get<WordGroup[]>('/wordbook/groups')
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

  async clearEntryGroup(entryId: number): Promise<void> {
    await apiClient.delete(`/wordbook/${entryId}/group`)
  },
}
