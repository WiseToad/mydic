import { defineStore } from 'pinia'
import { ref } from 'vue'
import { wordbookApi } from '@/api/wordbook'
import { normalizeText } from '@/utils/text'
import { extractErrorMessage } from '@/utils/error'
import { useToastStore } from '@/stores/toast'
import type { WordbookEntry, WordbookEntryCreate, WordbookEntryUpdate } from '@/types'

export const useWordbookStore = defineStore('wordbook', () => {
  const entries = ref<WordbookEntry[]>([])
  const isLoading = ref(false)
  const isLoaded = ref(false)

  async function fetchEntries(groupId: number, langPairs?: string[]) {
    isLoading.value = true
    try {
      entries.value = await wordbookApi.list(groupId, langPairs && langPairs.length > 0 ? langPairs : undefined)
      isLoaded.value = true
    } catch (e: unknown) {
      useToastStore().error(extractErrorMessage(e, 'Failed to load wordbook'))
    } finally {
      isLoading.value = false
    }
  }

  async function addEntry(data: WordbookEntryCreate, groupId?: number): Promise<WordbookEntry> {
    return wordbookApi.create({
      ...data,
      source_text: normalizeText(data.source_text),
      target_text: normalizeText(data.target_text),
    }, groupId)
  }

  async function updateEntry(id: number, update: WordbookEntryUpdate): Promise<void> {
    const updated = await wordbookApi.update(id, update)
    const idx = entries.value.findIndex((e) => e.id === id)
    if (idx !== -1) entries.value[idx] = updated
  }

  async function deleteEntry(id: number): Promise<void> {
    await wordbookApi.remove(id)
    entries.value = entries.value.filter((e) => e.id !== id)
  }

  /**
   * Reorder entries to match the given id order. Applies a sparse position
   * scheme (1000, 2000, …) locally then persists only the changed slice via
   * a single PUT /wordbook/reorder call.
   * orderedIds should cover all entry ids in the current group view;
   * any missing ids are appended last.
   */
  function reorderEntries(orderedIds: number[]): void {
    const currentIds = entries.value.map((e) => e.id)

    const map = new Map(entries.value.map((e) => [e.id, e]))
    const reordered: WordbookEntry[] = []
    for (const id of orderedIds) {
      const entry = map.get(id)
      if (entry) reordered.push(entry)
    }
    const seen = new Set(orderedIds)
    for (const e of entries.value) {
      if (!seen.has(e.id)) reordered.push(e)
    }
    reordered.forEach((e, i) => { e.position = (i + 1) * 1000 })
    entries.value = reordered

    const n = Math.min(orderedIds.length, currentIds.length)
    let first = 0
    while (first < n && orderedIds[first] === currentIds[first]) first++
    let last = n - 1
    while (last >= first && orderedIds[last] === currentIds[last]) last--

    if (first > last) return

    wordbookApi.reorder({ ids: orderedIds.slice(first, last + 1), offset: first }).catch(() => {})
  }

  function reset() {
    entries.value = []
    isLoading.value = false
    isLoaded.value = false
  }

  return { entries, isLoading, isLoaded, fetchEntries, addEntry, updateEntry, deleteEntry, reorderEntries, reset }
})
