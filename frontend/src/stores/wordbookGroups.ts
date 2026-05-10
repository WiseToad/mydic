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

  async function fetchGroups(): Promise<void> {
    tabs.value = await wordbookApi.listGroups()
  }

  async function addTab(name: string): Promise<WordGroup> {
    const tab = await wordbookApi.createGroup(name)
    tabs.value.push(tab)
    return tab
  }

  async function renameTab(id: number, name: string): Promise<void> {
    const tab = await wordbookApi.updateGroup(id, { name })
    const idx = tabs.value.findIndex((t) => t.id === id)
    if (idx !== -1) tabs.value[idx] = tab
    // Refresh the embedded group reference on each entry that belongs to
    // this group so the badge label visible on cards in the "All" view
    // updates immediately, without a full wordbook re-fetch.
    const wordbookStore = useWordbookStore()
    for (const entry of wordbookStore.entries) {
      if (entry.group?.id === id) entry.group = { ...tab }
    }
  }

  async function deleteTab(id: number): Promise<void> {
    await wordbookApi.deleteGroup(id)
    tabs.value = tabs.value.filter((t) => t.id !== id)
    // Reflect server-side SET NULL on affected entries
    const wordbookStore = useWordbookStore()
    for (const entry of wordbookStore.entries) {
      if (entry.group?.id === id) entry.group = null
    }
  }

  /**
   * Assign or unassign an entry to a group via the API.
   * Reflects the change locally without a full re-fetch.
   */
  async function assignEntry(entryId: number, groupId: number | null): Promise<void> {
    if (groupId === null) {
      await wordbookApi.clearEntryGroup(entryId)
    } else {
      await wordbookApi.setEntryGroup(entryId, groupId)
    }
    const wordbookStore = useWordbookStore()
    const entry = wordbookStore.entries.find((e) => e.id === entryId)
    if (entry) {
      entry.group = groupId ? (tabs.value.find((t) => t.id === groupId) ?? null) : null
    }
  }

  /** Returns the group id the entry belongs to, or null. */
  function getAssignment(entryId: number): number | null {
    const wordbookStore = useWordbookStore()
    return wordbookStore.entries.find((e) => e.id === entryId)?.group?.id ?? null
  }

  /**
   * Reorder tabs to match the given id order. Reassigns sparse positions
   * (n*1000 … 1000) and fires background PATCH calls to persist the new
   * order. Mirrors the wordbook entry reorderEntries pattern.
   * orderedIds should cover all tab ids; any missing ids are appended last.
   */
  function reorderTabs(orderedIds: number[]): void {
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
    Promise.all(
      reordered.map((t, i) =>
        wordbookApi.updateGroup(t.id, { position: (i + 1) * 1000 }).catch(() => {}),
      ),
    )
  }

  function reset() {
    tabs.value = []
  }

  return { tabs, fetchGroups, addTab, renameTab, deleteTab, assignEntry, getAssignment, reorderTabs, reset }
})
