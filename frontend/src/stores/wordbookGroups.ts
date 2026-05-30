import { defineStore } from 'pinia'
import { ref } from 'vue'
import { wordbookApi } from '@/api/wordbook'
import { useWordbookStore } from '@/stores/wordbook'
import type { WordGroup } from '@/types'

export type { WordGroup }

// Remove legacy localStorage key if present
try { localStorage.removeItem('lb_wordbook_groups') } catch { /* ignore */ }

export const useWordbookGroupsStore = defineStore('wordbookGroups', () => {
  const tabs = ref<WordGroup[]>([])
  const langPairs = ref<string[]>([])

  async function fetchGroups(filterLangPairs?: string[]): Promise<void> {
    tabs.value = await wordbookApi.listGroups(
      filterLangPairs && filterLangPairs.length > 0 ? filterLangPairs : undefined
    )
  }

  async function fetchLangPairs(): Promise<void> {
    langPairs.value = await wordbookApi.listLangPairs()
  }

  async function addTab(name: string): Promise<WordGroup> {
    const tab = await wordbookApi.createGroup(name)
    tabs.value.push(tab)
    // New group may affect available lang-pairs display; refresh lazily.
    fetchLangPairs().catch(() => {})
    return tab
  }

  async function renameTab(id: number, name: string): Promise<void> {
    const tab = await wordbookApi.updateGroup(id, { name })
    const idx = tabs.value.findIndex((t) => t.id === id)
    if (idx !== -1) tabs.value[idx] = tab
    // Update the cached group name on any currently-displayed entries.
    const wordbookStore = useWordbookStore()
    for (const entry of wordbookStore.entries) {
      if (entry.group.id === id) entry.group = { ...tab }
    }
  }

  async function deleteTab(id: number): Promise<void> {
    await wordbookApi.deleteGroup(id)
    tabs.value = tabs.value.filter((t) => t.id !== id)
    // Entries are deleted server-side via CASCADE; refresh lang-pairs.
    fetchLangPairs().catch(() => {})
  }

  /**
   * Move an entry to a different group via the API.
   * Removes it from the currently-displayed entries list immediately.
   */
  async function assignEntry(entryId: number, groupId: number): Promise<void> {
    await wordbookApi.setEntryGroup(entryId, groupId)
    // The entry has moved out of the current group view — remove it locally.
    const wordbookStore = useWordbookStore()
    wordbookStore.entries.splice(
      wordbookStore.entries.findIndex((e) => e.id === entryId), 1,
    )
  }

  /**
   * Move sourceId to the position of targetId among tabs. Applies a sparse
   * position scheme (1000, 2000, …) locally and persists via
   * PUT /wordbook/groups/reorder with just the two involved IDs.
   */
  function reorderTabs(sourceId: number, targetId: number): void {
    const ids = tabs.value.map((t) => t.id)
    const srcIdx = ids.indexOf(sourceId)
    const tgtIdx = ids.indexOf(targetId)
    if (srcIdx === -1 || tgtIdx === -1 || srcIdx === tgtIdx) return

    const movingForward = srcIdx < tgtIdx
    const newIds = ids.filter((id) => id !== sourceId)
    const insertAt = newIds.indexOf(targetId)
    newIds.splice(movingForward ? insertAt + 1 : insertAt, 0, sourceId)

    const map = new Map(tabs.value.map((t) => [t.id, t]))
    const reordered: WordGroup[] = newIds.map((id) => map.get(id)!)
    reordered.forEach((t, i) => { t.position = (i + 1) * 1000 })
    tabs.value = reordered

    wordbookApi.reorderGroups({ source_id: sourceId, target_id: targetId }).catch(() => {})
  }

  function reset() {
    tabs.value = []
    langPairs.value = []
  }

  return { tabs, langPairs, fetchGroups, fetchLangPairs, addTab, renameTab, deleteTab, assignEntry, reorderTabs, reset }
})
