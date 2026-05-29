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
   * Reorder tabs to match the given id order. Applies a sparse position
   * scheme (1000, 2000, …) locally then persists only the changed slice via
   * a single PUT /wordbook/groups/reorder call.
   */
  function reorderTabs(orderedIds: number[]): void {
    const currentIds = tabs.value.map((t) => t.id)

    const map = new Map(tabs.value.map((t) => [t.id, t]))
    const reordered: WordGroup[] = []
    for (const id of orderedIds) {
      const tab = map.get(id)
      if (tab) reordered.push(tab)
    }
    const seen = new Set(orderedIds)
    for (const t of tabs.value) {
      if (!seen.has(t.id)) reordered.push(t)
    }
    reordered.forEach((t, i) => { t.position = (i + 1) * 1000 })
    tabs.value = reordered

    const n = Math.min(orderedIds.length, currentIds.length)
    let first = 0
    while (first < n && orderedIds[first] === currentIds[first]) first++
    let last = n - 1
    while (last >= first && orderedIds[last] === currentIds[last]) last--

    if (first > last) return

    wordbookApi.reorderGroups({ ids: orderedIds.slice(first, last + 1), offset: first }).catch(() => {})
  }

  function reset() {
    tabs.value = []
    langPairs.value = []
  }

  return { tabs, langPairs, fetchGroups, fetchLangPairs, addTab, renameTab, deleteTab, assignEntry, reorderTabs, reset }
})
