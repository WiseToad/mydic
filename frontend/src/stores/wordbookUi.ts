import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'
import type { Definition, ContextExample } from '@/types'

/**
 * In-memory content cache for the details panel. NOT persisted to localStorage.
 * undefined = never fetched or last fetch errored (panel will fetch fresh).
 * null (defData) / [] (ctxData/lexData) = fetched and found nothing.
 */
export interface EntryDetailsContent {
  defData?: Definition | null   // undefined = not cached; null = not found
  ctxData?: ContextExample[]    // undefined = not cached; [] = none found
  lexData?: string[]            // undefined = not cached; [] = none found
}

export interface EntryUiState {
  hintVisible?: boolean                              // translation hint revealed
  detailsTab?: 'definition' | 'context' | 'lexical'  // last active tab in the details panel
  defProvider?: string | null                        // last used definition provider code
  ctxProvider?: string | null                        // last used context provider code
  lexProvider?: string | null                        // last used lexical provider code
}

export type DensityLevel = 'compact' | 'normal' | 'spacious'

interface GlobalPrefs {
  density: DensityLevel
  activeLangs: string[]     // empty = show all languages
  activeColors: string[]    // empty = show all colors; 'none' matches uncolored entries
  activeGroupId: number | null  // null = show all groups
  showTranslations?: boolean       // when set, overrides all per-entry hintVisible flags
  sidePanelVisible?: boolean  // vertical word list panel on the right
  swapDisplay?: boolean     // show target word as primary, source as hint
}

type UiMap = Record<number, EntryUiState>

const DEFAULT_PREFS: GlobalPrefs = { density: 'normal', activeLangs: [], activeColors: [], activeGroupId: null, showTranslations: undefined, sidePanelVisible: false, swapDisplay: false }

interface StorageNode {
  entriesByGroup?: Record<string, UiMap>  // keyed by String(groupId)
  density?: DensityLevel
  activeLangs?: string[]
  activeColors?: string[]
  activeGroupId?: number | null
  showTranslations?: boolean
  sidePanelVisible?: boolean
  swapDisplay?: boolean
}

/** Namespaced localStorage key for the current user's wordbook UI state. */
function _storageKey(userId?: number): string {
  if (userId !== undefined) return `mydicWordbookView${userId}`
  const raw = localStorage.getItem('mydicUserId')
  const uid = raw !== null ? Number(raw) : NaN
  return !isNaN(uid) ? `mydicWordbookView${uid}` : 'mydicWordbookView'
}

function _readNode(userId?: number): StorageNode {
  try {
    const raw = localStorage.getItem(_storageKey(userId))
    if (!raw) return {}
    return JSON.parse(raw) as StorageNode
  } catch {
    return {}
  }
}

function loadGroupEntries(groupId: number, userId?: number): UiMap {
  try {
    const node = _readNode(userId)
    return node.entriesByGroup?.[String(groupId)] ?? {}
  } catch {
    return {}
  }
}

function saveGroupEntries(groupId: number, map: UiMap): void {
  try {
    const key = _storageKey()
    const node = _readNode()
    if (!node.entriesByGroup) node.entriesByGroup = {}
    node.entriesByGroup[String(groupId)] = map
    localStorage.setItem(key, JSON.stringify(node))
  } catch {
    localStorage.removeItem(_storageKey())
  }
}

function deleteStoredGroupEntries(groupId: number): void {
  try {
    const key = _storageKey()
    const node = _readNode()
    if (node.entriesByGroup) {
      delete node.entriesByGroup[String(groupId)]
      localStorage.setItem(key, JSON.stringify(node))
    }
  } catch {}
}

function loadPrefs(userId?: number): GlobalPrefs {
  try {
    const node = _readNode(userId)
    if (node.density === undefined) return { ...DEFAULT_PREFS }
    // Migrate: old activeGroupId was a string ("g_..."); now it must be a number.
    const rawTabId = node.activeGroupId
    const activeGroupId: number | null =
      typeof rawTabId === 'number' ? rawTabId : null
    // Older saved prefs may not have activeColors; default-merge it.
    const activeColors = Array.isArray(node.activeColors) ? node.activeColors : []
    // Explicitly pick only known GlobalPrefs fields — never include entriesByGroup.
    // If entriesByGroup were spread into prefs.value, savePrefs would later write
    // a stale snapshot back to localStorage, corrupting per-entry tab state.
    return {
      ...DEFAULT_PREFS,
      density: node.density,
      activeLangs: node.activeLangs ?? DEFAULT_PREFS.activeLangs,
      activeGroupId,
      activeColors,
      showTranslations: node.showTranslations,
      sidePanelVisible: node.sidePanelVisible,
      swapDisplay: node.swapDisplay,
    }
  } catch {
    return { ...DEFAULT_PREFS }
  }
}

function savePrefs(p: GlobalPrefs) {
  try {
    const key = _storageKey()
    const node = _readNode()
    localStorage.setItem(key, JSON.stringify({ entriesByGroup: node.entriesByGroup, ...p }))
  } catch {}
}

export const useWordbookUiStore = defineStore('wordbookUi', () => {
  const _currentGroupId = ref<number | null>(null)
  const map = ref<UiMap>({})
  const prefs = ref<GlobalPrefs>(loadPrefs())

  // ── In-memory details content cache (not persisted) ─────────────────────────
  const _detailsContent = new Map<number, EntryDetailsContent>()

  function getDetailsContent(id: number): EntryDetailsContent | undefined {
    return _detailsContent.get(id)
  }

  function patchDetailsContent(id: number, patch: Partial<EntryDetailsContent>): void {
    const existing = _detailsContent.get(id) ?? {}
    _detailsContent.set(id, { ...existing, ...patch })
  }

  function clearDetailsContent(id: number): void {
    _detailsContent.delete(id)
  }

  // --- Global prefs ---

  const density = computed<DensityLevel>({
    get: () => prefs.value.density,
    set: (v) => {
      if (v === 'compact') activeCardId.value = null
      prefs.value.density = v
      savePrefs(prefs.value)
    },
  })

  const activeLangs = computed<string[]>({
    get: () => prefs.value.activeLangs,
    set: (v) => { prefs.value.activeLangs = v; savePrefs(prefs.value) },
  })

  const activeColors = computed<string[]>({
    get: () => prefs.value.activeColors,
    set: (v) => { prefs.value.activeColors = v; savePrefs(prefs.value) },
  })

  const activeGroupId = computed<number | null>({
    get: () => prefs.value.activeGroupId,
    set: (v) => { prefs.value.activeGroupId = v; savePrefs(prefs.value) },
  })

  /**
   * Ensure activeGroupId is always set to a valid group when groups exist.
   * Called after fetchGroups (on mount and after lang-pair filter changes).
   * - If the saved activeGroupId is still in the list, keep it.
   * - Otherwise default to the first group.
   * - If the list is empty, set null.
   */
  function initActiveGroup(groups: { id: number }[]) {
    if (groups.length === 0) {
      prefs.value.activeGroupId = null
      savePrefs(prefs.value)
      return
    }
    const current = prefs.value.activeGroupId
    if (current !== null && groups.some((g) => g.id === current)) return
    prefs.value.activeGroupId = groups[0].id
    savePrefs(prefs.value)
  }

  const sidePanelVisible = computed<boolean>({
    get: () => prefs.value.sidePanelVisible ?? false,
    set: (v) => { prefs.value.sidePanelVisible = v; savePrefs(prefs.value) },
  })

  const swapDisplay = computed<boolean>({
    get: () => prefs.value.swapDisplay ?? false,
    set: (v) => { prefs.value.swapDisplay = v; savePrefs(prefs.value) },
  })

  // --- Per-card overlay state ---

  /**
   * The single card that currently has an open overlay.
   * activeCardMode distinguishes between the details panel and the edit form.
   * Closing either always sets activeCardId back to null.
   */
  const activeCardId = ref<number | null>(null)
  const activeCardMode = ref<'details' | 'editing'>('details')

  /** The single card whose actions popup menu is currently open. */
  const activeMenuId = ref<number | null>(null)

  /**
   * Transient: the card currently being visually highlighted (brief flash to
   * draw the user's eye after a scroll-to action). Null when nothing is
   * highlighted. Managed by highlightEntry() below.
   */
  const highlightId = ref<number | null>(null)
  const highlightSeq = ref(0)

  /**
   * Transient: set by the Translator view just before navigating to the
   * Wordbook view, so the Wordbook view can scroll to the matching card and
   * highlight it once it renders. Consumers should call
   * consumePendingHighlight() to read + clear it.
   */
  const pendingHighlightId = ref<number | null>(null)

  // ── Per-group focused entry and open-details (in-memory only) ─────────────────
  /**
   * Tracks the focused entry id per group. Key = group id (null = ungrouped).
   * At most one focused entry per group. Not persisted.
   */
  const focusedByGroup = reactive(new Map<number | null, number>())

  /**
   * Tracks which card's details panel was open per group. Populated by
   * saveOpenDetailsForGroup on navigation / tab-switch; read by
   * getOpenDetailsForGroup on return. Not persisted.
   */
  const openDetailsByGroup = reactive(new Map<number | null, number>())

  function getState(id: number): EntryUiState {
    return map.value[id] ?? {}
  }

  /**
   * Read entry UI state scoped to the entry's own group.
   * When groupId matches the currently loaded group, reads from the reactive
   * in-memory map (fast, reactive). Otherwise reads directly from the entry's
   * group storage — safe during group-switch transitions when old-group
   * components are still mounted but a different group is already loaded.
   */
  function getStateForGroup(id: number, groupId: number | null): EntryUiState {
    if (groupId === _currentGroupId.value) return map.value[id] ?? {}
    if (groupId === null) return {}
    return loadGroupEntries(groupId)[id] ?? {}
  }

  function getReactive(id: number, _key: 'hintVisible'): boolean {
    const perEntry = map.value[id]?.hintVisible
    if (perEntry !== undefined) return perEntry
    return prefs.value.showTranslations ?? false
  }

  function getReactiveForGroup(id: number, groupId: number | null, _key: 'hintVisible'): boolean {
    const perEntry = getStateForGroup(id, groupId).hintVisible
    if (perEntry !== undefined) return perEntry
    return prefs.value.showTranslations ?? false
  }

  function getProvider(id: number, key: 'def' | 'ctx' | 'lex'): string | null | undefined {
    const state = map.value[id]
    if (key === 'def') return state?.defProvider
    if (key === 'ctx') return state?.ctxProvider
    return state?.lexProvider
  }

  function getProviderForGroup(id: number, groupId: number | null, key: 'def' | 'ctx' | 'lex'): string | null | undefined {
    const state = getStateForGroup(id, groupId)
    if (key === 'def') return state.defProvider
    if (key === 'ctx') return state.ctxProvider
    return state.lexProvider
  }

  function setState(id: number, patch: Partial<EntryUiState>) {
    map.value[id] = { ...map.value[id], ...patch }
    if (_currentGroupId.value !== null) saveGroupEntries(_currentGroupId.value, map.value)
  }

  /**
   * Write entry UI state scoped to the entry's own group.
   * When groupId matches the currently loaded group, updates the reactive
   * in-memory map and saves it. Otherwise, loads the target group's storage,
   * applies the patch, and saves — without touching map.value.
   * This prevents cross-group state corruption during group-switch transitions.
   */
  function setStateForGroup(id: number, groupId: number | null, patch: Partial<EntryUiState>): void {
    if (groupId === _currentGroupId.value) {
      map.value[id] = { ...map.value[id], ...patch }
      if (_currentGroupId.value !== null) saveGroupEntries(_currentGroupId.value, map.value)
    } else if (groupId !== null) {
      const otherMap = loadGroupEntries(groupId)
      otherMap[id] = { ...otherMap[id], ...patch }
      saveGroupEntries(groupId, otherMap)
    }
  }

  function setProvider(id: number, key: 'def' | 'ctx' | 'lex', code: string | null): void {
    if (key === 'def') setState(id, { defProvider: code })
    else if (key === 'ctx') setState(id, { ctxProvider: code })
    else setState(id, { lexProvider: code })
  }

  function setProviderForGroup(id: number, groupId: number | null, key: 'def' | 'ctx' | 'lex', code: string | null): void {
    if (key === 'def') setStateForGroup(id, groupId, { defProvider: code })
    else if (key === 'ctx') setStateForGroup(id, groupId, { ctxProvider: code })
    else setStateForGroup(id, groupId, { lexProvider: code })
  }

  /** Mark `entryId` as the focused entry for the given group. */
  function setFocusedEntry(entryId: number, groupId: number | null): void {
    focusedByGroup.set(groupId, entryId)
  }

  /**
   * Returns the focused entry id for `groupId`, or `undefined` if none.
   * Reactive: a computed that calls this will re-evaluate when the focused
   * entry for that specific group changes.
   */
  function getFocusedEntry(groupId: number | null): number | undefined {
    return focusedByGroup.get(groupId)
  }

  /**
   * Clear whichever group currently has `entryId` as its focused entry.
   * Called when an entry is deleted or moved out of its group.
   */
  function clearFocusedEntryById(entryId: number): void {
    for (const [gid, eid] of focusedByGroup) {
      if (eid === entryId) {
        focusedByGroup.delete(gid)
        break
      }
    }
  }

  /**
   * Snapshot the currently-open card for `groupId`. Clears the saved state
   * when nothing is open, so closing a card then navigating away does not
   * reopen it on return. An in-progress edit is treated as the card to
   * restore in details mode (edit is cancelled on return).
   */
  function saveOpenDetailsForGroup(groupId: number | null): void {
    if (activeCardId.value !== null) openDetailsByGroup.set(groupId, activeCardId.value)
    else openDetailsByGroup.delete(groupId)
  }

  /** Return the saved open-card id for `groupId`, or undefined if none. */
  function getOpenDetailsForGroup(groupId: number | null): number | undefined {
    return openDetailsByGroup.get(groupId)
  }

  /**
   * Efficiently toggle all hints at once.
   * – Strips hintVisible from every per-entry record (saves storage space).
   * – Sets showTranslations = true in prefs when showing, removes it when hiding.
   * Per-entry flags set afterwards by individual toggles override the global.
   */
  function setAllHints(show: boolean) {
    for (const k of Object.keys(map.value)) {
      const n = Number(k)
      if ('hintVisible' in (map.value[n] ?? {})) {
        delete map.value[n].hintVisible
      }
    }
    if (_currentGroupId.value !== null) saveGroupEntries(_currentGroupId.value, map.value)
    if (show) {
      prefs.value.showTranslations = true
    } else {
      delete prefs.value.showTranslations
    }
    savePrefs(prefs.value)
  }

  const showTranslations = computed(() => prefs.value.showTranslations ?? false)

  /** Toggle the details panel; collapses any other open overlay first. */
  function toggleDetails(id: number) {
    if (activeCardId.value === id && activeCardMode.value === 'details') {
      activeCardId.value = null
    } else {
      activeCardId.value = id
      activeCardMode.value = 'details'
    }
  }

  /** Open the edit form; collapses any other open overlay first. */
  function openEditing(id: number) {
    activeCardId.value = id
    activeCardMode.value = 'editing'
  }

  /** Close whatever overlay is currently open. */
  function closeActive() {
    activeCardId.value = null
  }

  /** Briefly flash a card to draw the user's eye. */
  function highlightEntry(id: number) {
    highlightId.value = id
    highlightSeq.value++
  }

  /**
   * Called by WordbookEntry when its flash animation ends. Clears
   * `highlightId` so the side-panel active indicator turns off in sync.
   */
  function clearHighlight() {
    highlightId.value = null
  }

  /**
   * Queue the given entry id for a scroll-to-and-highlight action on the
   * next render of the Wordbook view. Adjusts only the filter(s) that would
   * hide the target card so unrelated active filters are preserved:
   *   - lang-pair filter active but missing `pair`    → add `pair` to the list
   *   - group filter active but on a different group  → switch to `entryGroupId`
   *     (if the entry has no group, clears the filter — nothing to switch to)
   *   - color filter active but missing entry's color → add that color to the list
   */
  function requestShowEntry(
    id: number,
    pair: string,  // 'src:tgt' format
    entryGroupId: number | null,
    entryColor: string | null,
  ) {
    let changed = false
    if (prefs.value.activeLangs.length > 0 && !prefs.value.activeLangs.includes(pair)) {
      prefs.value.activeLangs = [...prefs.value.activeLangs, pair]
      changed = true
    }
    if (prefs.value.activeGroupId !== null && prefs.value.activeGroupId !== entryGroupId) {
      prefs.value.activeGroupId = entryGroupId
      changed = true
    }
    if (prefs.value.activeColors.length > 0) {
      const colorKey = entryColor ?? 'none'
      if (!prefs.value.activeColors.includes(colorKey)) {
        prefs.value.activeColors = [...prefs.value.activeColors, colorKey]
        changed = true
      }
    }
    if (changed) savePrefs(prefs.value)
    pendingHighlightId.value = id
  }

  /** Read and clear the pending highlight id (one-shot consumer). */
  function consumePendingHighlight(): number | null {
    const id = pendingHighlightId.value
    pendingHighlightId.value = null
    return id
  }

  /** Remove stale keys for entries that no longer exist. */
  function prune(validIds: number[]) {
    const set = new Set(validIds)
    if (activeCardId.value !== null && !set.has(activeCardId.value)) {
      activeCardId.value = null
    }
    let changed = false
    for (const k of Object.keys(map.value)) {
      if (!set.has(Number(k))) {
        delete map.value[Number(k)]
        _detailsContent.delete(Number(k))
        changed = true
      }
    }
    if (changed && _currentGroupId.value !== null) saveGroupEntries(_currentGroupId.value, map.value)
    // Only prune the focused entry for the currently-loaded group.
    // Entries in other groups are not in memory — their focused IDs remain valid.
    const currentGid = _currentGroupId.value
    const focusedInCurrentGroup = focusedByGroup.get(currentGid)
    if (focusedInCurrentGroup !== undefined && !set.has(focusedInCurrentGroup)) {
      focusedByGroup.delete(currentGid)
    }
  }

  /**
   * Load the item-state map for `groupId` and make it the active map.
   * Pass null to clear (when no group is selected).
   *
   * Flushes the current in-memory state to localStorage before swapping so
   * that any state accumulated since the last setState call (e.g. after a
   * loadGroupEntries reload with no subsequent user action) is always
   * persisted before the map is replaced.
   */
  function switchGroup(groupId: number | null): void {
    if (_currentGroupId.value === groupId) return
    if (_currentGroupId.value !== null) {
      saveGroupEntries(_currentGroupId.value, map.value)
    }
    _currentGroupId.value = groupId
    map.value = groupId !== null ? loadGroupEntries(groupId) : {}
  }

  /**
   * Remove the persisted item-state bunch for a deleted group and clear
   * in-memory state if that group is currently active.
   */
  function deleteGroupEntries(groupId: number): void {
    deleteStoredGroupEntries(groupId)
    openDetailsByGroup.delete(groupId)
    if (_currentGroupId.value === groupId) {
      _currentGroupId.value = null
      map.value = {}
    }
  }

  function reinitialize(userId: number): void {
    _currentGroupId.value = null
    map.value = {}
    _detailsContent.clear()
    prefs.value = loadPrefs(userId)
    activeCardId.value = null
    activeCardMode.value = 'details'
    activeMenuId.value = null
    highlightId.value = null
    highlightSeq.value = 0
    pendingHighlightId.value = null
    focusedByGroup.clear()
    openDetailsByGroup.clear()
  }

  return {
    getState, setState, prune, getReactive, getProvider, setProvider,
    getStateForGroup, setStateForGroup, getReactiveForGroup, getProviderForGroup, setProviderForGroup,
    getDetailsContent, patchDetailsContent, clearDetailsContent,
    activeCardId, activeCardMode,
    toggleDetails, openEditing, closeActive,
    activeMenuId,
    setAllHints, showTranslations,
    density, activeLangs, activeColors, activeGroupId, sidePanelVisible, swapDisplay,
    highlightId, highlightSeq, pendingHighlightId,
    highlightEntry, clearHighlight, requestShowEntry, consumePendingHighlight,
    setFocusedEntry, getFocusedEntry, clearFocusedEntryById,
    saveOpenDetailsForGroup, getOpenDetailsForGroup,
    initActiveGroup,
    switchGroup, deleteGroupEntries, reinitialize,
  }
})
