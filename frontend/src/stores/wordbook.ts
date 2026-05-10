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

  async function fetchEntries() {
    isLoading.value = true
    try {
      entries.value = await wordbookApi.list()
      isLoaded.value = true
    } catch (e: unknown) {
      useToastStore().error(extractErrorMessage(e, 'Failed to load wordbook'))
    } finally {
      isLoading.value = false
    }
  }

  async function addEntry(data: WordbookEntryCreate): Promise<WordbookEntry> {
    const entry = await wordbookApi.create({
      ...data,
      source_text: normalizeText(data.source_text),
      target_text: normalizeText(data.target_text),
    })
    entries.value.unshift(entry)  // newest first
    return entry
  }

  function findDuplicate(sourceLang: string, targetLang: string, sourceText: string): WordbookEntry | null {
    const normalized = normalizeText(sourceText)
    return entries.value.find(
      (e) => e.source_lang === sourceLang && e.target_lang === targetLang && normalizeText(e.source_text) === normalized
    ) ?? null
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

  async function batchDeleteEntries(ids: number[]): Promise<void> {
    if (ids.length === 0) return
    await wordbookApi.batchRemove(ids)
    const idSet = new Set(ids)
    entries.value = entries.value.filter((e) => !idSet.has(e.id))
  }

  /**
   * Reorder entries to match the given id order. Reassigns sparse positions
   * (n*1000 … 1000) and fires background PATCH calls to persist the new order.
   * orderedIds should cover all entry ids; any missing ids are appended last.
   */
  function reorderEntries(orderedIds: number[]): void {
    const map = new Map(entries.value.map((e) => [e.id, e]))
    const reordered: WordbookEntry[] = []
    for (const id of orderedIds) {
      const entry = map.get(id)
      if (entry) reordered.push(entry)
    }
    // Append any entries not covered by orderedIds
    const seen = new Set(orderedIds)
    for (const e of entries.value) {
      if (!seen.has(e.id)) reordered.push(e)
    }
    // Assign sparse positions so server returns them in the right order
    const n = reordered.length
    reordered.forEach((e, i) => { e.position = (n - i) * 1000 })
    entries.value = reordered
    // Background sync — ignore individual failures, non-critical
    Promise.all(
      reordered.map((e, i) =>
        wordbookApi.update(e.id, { position: (n - i) * 1000 }).catch(() => {}),
      ),
    )
  }

  function reset() {
    entries.value = []
    isLoading.value = false
    isLoaded.value = false
  }

  return { entries, isLoading, isLoaded, fetchEntries, addEntry, updateEntry, deleteEntry, batchDeleteEntries, findDuplicate, reorderEntries, reset }
})
