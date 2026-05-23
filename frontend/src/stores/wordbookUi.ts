import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export interface EntryUiState {
  hintVisible?: boolean                              // translation hint revealed
  contextOpen?: boolean                              // saved context examples expanded
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

// Legacy keys superseded by mydicWordbookView
const LEGACY_UI_KEY = 'lb_wordbook_ui'
const LEGACY_PROV_KEY = 'lb_wb_lexical_providers'

const DEFAULT_PREFS: GlobalPrefs = { density: 'normal', activeLangs: [], activeColors: [], activeGroupId: null, showTranslations: undefined, sidePanelVisible: false, swapDisplay: false }

interface StorageNode {
  entries?: UiMap
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


function load(userId?: number): UiMap {
  try {
    const node = _readNode(userId)
    if (node.entries !== undefined) return node.entries

    if (userId !== undefined) return {}

    // One-time migration from legacy separate keys
    const oldUiRaw = localStorage.getItem(LEGACY_UI_KEY)
    const oldProvRaw = localStorage.getItem(LEGACY_PROV_KEY)
    if (!oldUiRaw && !oldProvRaw) return {}

    const oldUi: UiMap = oldUiRaw ? JSON.parse(oldUiRaw) : {}
    const oldProv: Record<number, { def?: string | null; ctx?: string | null }> =
      oldProvRaw ? JSON.parse(oldProvRaw) : {}
    const merged: UiMap = { ...oldUi }
    for (const id of Object.keys(oldProv)) {
      const n = Number(id)
      const p = oldProv[n]
      merged[n] = { ...merged[n], defProvider: p.def, ctxProvider: p.ctx }
    }
    save(merged)
    localStorage.removeItem(LEGACY_UI_KEY)
    localStorage.removeItem(LEGACY_PROV_KEY)
    return merged
  } catch {
    return {}
  }
}

function save(map: UiMap) {
  try {
    const key = _storageKey()
    const node = _readNode()
    node.entries = map
    localStorage.setItem(key, JSON.stringify(node))
  } catch {
    localStorage.removeItem(_storageKey())
  }
}

function loadPrefs(userId?: number): GlobalPrefs {
  try {
    const node = _readNode(userId)
    if (node.density === undefined) return { ...DEFAULT_PREFS }
    const parsed = node as Partial<GlobalPrefs>
    // Migrate: old activeGroupId was a string ("g_..."); now it must be a number.
    const rawTabId = parsed.activeGroupId
    const activeGroupId: number | null =
      typeof rawTabId === 'number' ? rawTabId : null
    // Older saved prefs may not have activeColors; default-merge it.
    const activeColors = Array.isArray(parsed.activeColors) ? parsed.activeColors : []
    return { ...DEFAULT_PREFS, ...parsed, activeGroupId, activeColors }
  } catch {
    return { ...DEFAULT_PREFS }
  }
}

function savePrefs(p: GlobalPrefs) {
  try {
    const key = _storageKey()
    const node = _readNode()
    localStorage.setItem(key, JSON.stringify({ entries: node.entries, ...p }))
  } catch {}
}

export const useWordbookUiStore = defineStore('wordbookUi', () => {
  const map = ref<UiMap>(load())
  const prefs = ref<GlobalPrefs>(loadPrefs())

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

  function getState(id: number): EntryUiState {
    return map.value[id] ?? {}
  }

  function getReactive(id: number, key: 'hintVisible' | 'contextOpen'): boolean {
    if (key === 'hintVisible') {
      const perEntry = map.value[id]?.hintVisible
      if (perEntry !== undefined) return perEntry
      return prefs.value.showTranslations ?? false
    }
    return map.value[id]?.[key] ?? false
  }

  function getProvider(id: number, key: 'def' | 'ctx' | 'lex'): string | null | undefined {
    const state = map.value[id]
    if (key === 'def') return state?.defProvider
    if (key === 'ctx') return state?.ctxProvider
    return state?.lexProvider
  }

  function setState(id: number, patch: Partial<EntryUiState>) {
    map.value[id] = { ...map.value[id], ...patch }
    save(map.value)
  }

  function setProvider(id: number, key: 'def' | 'ctx' | 'lex', code: string | null): void {
    if (key === 'def') setState(id, { defProvider: code })
    else if (key === 'ctx') setState(id, { ctxProvider: code })
    else setState(id, { lexProvider: code })
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
    save(map.value)
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
    pair: string,
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
        changed = true
      }
    }
    if (changed) save(map.value)
  }

  function reinitialize(userId: number) {
    map.value = load(userId)
    prefs.value = loadPrefs(userId)
    activeCardId.value = null
    activeCardMode.value = 'details'
    activeMenuId.value = null
    highlightId.value = null
    highlightSeq.value = 0
    pendingHighlightId.value = null
  }

  return {
    getState, setState, prune, getReactive, getProvider, setProvider,
    activeCardId, activeCardMode,
    toggleDetails, openEditing, closeActive,
    activeMenuId,
    setAllHints, showTranslations,
    density, activeLangs, activeColors, activeGroupId, sidePanelVisible, swapDisplay,
    highlightId, highlightSeq, pendingHighlightId,
    highlightEntry, clearHighlight, requestShowEntry, consumePendingHighlight,
    reinitialize,
  }
})
