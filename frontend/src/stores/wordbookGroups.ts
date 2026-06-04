import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
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
    if (wordbookStore.totalEntries > 0) wordbookStore.totalEntries--
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

  /**
   * Restore tabs to the given full ordered ID list. Used by the undo callback
   * after a reorderTabs call. Mirrors the reorderEntries pattern.
   */
  function restoreTabsOrder(orderedIds: number[], sourceId: number, targetId: number): void {
    const map = new Map(tabs.value.map((t) => [t.id, t]))
    const reordered: WordGroup[] = []
    for (const id of orderedIds) {
      const t = map.get(id)
      if (t) reordered.push(t)
    }
    const seen = new Set(orderedIds)
    for (const t of tabs.value) {
      if (!seen.has(t.id)) reordered.push(t)
    }
    reordered.forEach((t, i) => { t.position = (i + 1) * 1000 })
    tabs.value = reordered
    wordbookApi.reorderGroups({ source_id: sourceId, target_id: targetId }).catch(() => {})
  }

  /** Groups that matched the last lang-pair filter (in_filter=true). When no
   * filter was supplied all groups qualify. Use this in the Wordbook view to
   * show only relevant groups; the Translator popup uses `tabs` directly so
   * it can display (and gray out) groups outside the current filter. */
  const filteredTabs = computed(() => tabs.value.filter((t) => t.in_filter !== false))

  function reset() {
    tabs.value = []
    langPairs.value = []
  }

  return { tabs, filteredTabs, langPairs, fetchGroups, fetchLangPairs, addTab, renameTab, deleteTab, assignEntry, reorderTabs, restoreTabsOrder, reset }
})
