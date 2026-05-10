import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { translateApi } from '@/api/translate'
import { normalizeText } from '@/utils/text'
import { extractErrorMessage } from '@/utils/error'
import { useLanguageSettingsStore } from '@/stores/languageSettings'
import type { ContextExample, Definition, TranslateResponse, TranslatorHistoryEntry } from '@/types'

const MAX_HISTORY = 50

/** Shape written to localStorage: full history entry minus re-fetchable data. */
type PersistedEntry = Omit<TranslatorHistoryEntry, 'definition' | 'contextExamples' | 'lexicalMatches'>

interface StorageNode {
  history?: { entries: PersistedEntry[]; index: number }
  showCtxTranslations?: boolean
}

/** Namespaced localStorage key for the current user's translator state. */
function _storageKey(userId?: number): string {
  if (userId !== undefined) return `mydicTranslatorView${userId}`
  const raw = localStorage.getItem('mydicUserId')
  const uid = raw !== null ? Number(raw) : NaN
  return !isNaN(uid) ? `mydicTranslatorView${uid}` : 'mydicTranslatorView'
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

function loadCtxAllVisible(userId?: number): boolean {
  const v = _readNode(userId).showCtxTranslations
  return v === undefined ? true : v === true
}

function loadHistory(userId?: number): { entries: TranslatorHistoryEntry[]; index: number } {
  try {
    const persisted = _readNode(userId).history
    if (!persisted) return { entries: [], index: -1 }
    return { entries: persisted.entries as TranslatorHistoryEntry[], index: persisted.index }
  } catch {
    return { entries: [], index: -1 }
  }
}

function persistHistory(entries: TranslatorHistoryEntry[], index: number) {
  try {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const slim: PersistedEntry[] = entries.slice(-MAX_HISTORY).map(
      ({ definition, contextExamples, lexicalMatches, ...rest }) => rest
    )
    const key = _storageKey()
    const node = _readNode()
    node.history = { entries: slim, index: Math.min(index, slim.length - 1) }
    localStorage.setItem(key, JSON.stringify(node))
  } catch {
    localStorage.removeItem(_storageKey())
  }
}

export const useTranslatorStore = defineStore('translator', () => {
  // Restore persisted history on startup
  const _stored = loadHistory()

  // Current input state
  const inputText = ref('')
  const sourceLang = ref('auto')
  const targetLang = ref('')
  /** Last target lang before the most recent change; always differs from targetLang. */
  const prevTargetLang = ref<string | null>(null)
  const result = ref<TranslateResponse | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Undo/redo history stack — the SOLE source of truth for which provider was
  // used for any given translation / def / ctx / lex fetch.  No carry-over
  // refs live in the store; the view re-queries provider lists on navigation
  // and resolves the displayed code from the current entry + list.
  const history = ref<TranslatorHistoryEntry[]>(_stored.entries)
  const historyIndex = ref(_stored.index)

  // Global "show context translations" flag for the translator view's
  // ContextExamples panel.  Single value shared across all history entries:
  // navigating back/forward does NOT preserve a per-entry override, by design.
  const ctxAllVisible = ref<boolean>(loadCtxAllVisible())
  function setCtxAllVisible(v: boolean) {
    ctxAllVisible.value = v
    try {
      const key = _storageKey()
      const node = _readNode()
      node.showCtxTranslations = v
      localStorage.setItem(key, JSON.stringify(node))
    } catch {
      // localStorage quota or unavailable — ignore; in-memory state still works
    }
  }

  // Restore UI state before registering watches so they don't fire during init.
  if (_stored.index >= 0 && _stored.entries[_stored.index]) {
    const e = _stored.entries[_stored.index]
    inputText.value = e.sourceText
    sourceLang.value = e.sourceLang
    targetLang.value = e.targetLang
    result.value = e.result ?? null
  }

  // Keep prevTargetLang in sync: capture the old value on every targetLang change.
  watch(targetLang, (newVal, oldVal) => {
    if (newVal !== oldVal) prevTargetLang.value = oldVal
  }, { flush: 'sync' })

  const canGoBack = computed(() => historyIndex.value > 0)
  const canGoForward = computed(() => historyIndex.value < history.value.length - 1)
  const currentEntry = computed(() =>
    historyIndex.value >= 0 ? history.value[historyIndex.value] ?? null : null
  )

  /**
   * Pick an alternative target lang when the auto-detected source equals the current target.
   * Priority: prevTargetLang → first enabled lang that differs from detectedLang.
   */
  function _resolveTargetLangConflict(detectedLang: string): string {
    if (prevTargetLang.value && prevTargetLang.value !== detectedLang) return prevTargetLang.value
    const alt = useLanguageSettingsStore().enabledLangs.find(l => l.code !== detectedLang)
    return alt?.code ?? detectedLang
  }

  /** Push a completed translation into the undo/redo history stack. */
  function _pushToHistory(
    text: string, res: TranslateResponse, providerCode: string,
    overrideLexCode?: string | null,
    overrideDefCode?: string | null,
    overrideCtxCode?: string | null,
  ) {
    const last = history.value.length > 0 ? history.value[history.value.length - 1] : null
    const preLast = history.value.length > 1 ? history.value[history.value.length - 2] : null

    const matchesLast = last && last.sourceText === text && last.sourceLang === sourceLang.value && last.targetLang === targetLang.value && last.providerCode === providerCode
    const matchesPreLast = preLast && preLast.sourceText === text && preLast.sourceLang === sourceLang.value && preLast.targetLang === targetLang.value && preLast.providerCode === providerCode

    if (matchesLast) {
      historyIndex.value = history.value.length - 1
    } else if (matchesPreLast) {
      historyIndex.value = history.value.length - 2
    } else {
      // Override codes are stored verbatim.  `undefined` means "no preference
      // set" (fresh start — dropdowns fall back to their first-available
      // default); `null` means explicit "None"; a string is a specific code.
      // Callers are responsible for passing a validated carry value when they
      // want to inherit the current entry's preference.
      history.value.push({
        sourceText: text,
        sourceLang: sourceLang.value,
        targetLang: targetLang.value,
        providerCode,
        result: res,
        lexProviderCode: overrideLexCode,
        defProviderCode: overrideDefCode,
        ctxProviderCode: overrideCtxCode,
      })
      if (history.value.length > MAX_HISTORY) history.value.splice(0, history.value.length - MAX_HISTORY)
      historyIndex.value = history.value.length - 1
    }
  }

  /**
   * Resolve a translation provider for the current language pair when the
   * caller (typically `translateWord` from another component) does not have
   * the view's selected code at hand.  Returns the first enabled+available
   * provider's code, or null if none can serve the pair.
   */
  async function _resolveTranslationProvider(): Promise<string | null> {
    try {
      const list = await translateApi.getProviders(sourceLang.value, targetLang.value)
      return list.find(p => p.enabled && p.available)?.code ?? null
    } catch {
      return null
    }
  }

  /**
   * Translate current inputText using the supplied provider code and push
   * the result into history.  Backend now requires an explicit provider, so
   * a code MUST be available before the API call: when the caller passes
   * `null` the store resolves the first usable provider on its own
   * (typically only used for `translateWord` calls coming from outside the
   * translator view); the view's normal flow always passes the code
   * currently shown in its dropdown.
   */
  async function translate(
    providerCode: string | null = null,
    allowSameLangPair = false,
    overrideLexCode?: string | null,
    overrideDefCode?: string | null,
    overrideCtxCode?: string | null,
  ) {
    if (isLoading.value) return

    const text = normalizeText(inputText.value)
    if (!text) return
    inputText.value = text  // write normalized value back to input

    // Clear any stale error synchronously before async work so it is not
    // visible during provider resolution (prevents the swap-button flicker
    // where the old "no providers" error briefly shows in red).
    error.value = null
    let code = providerCode
    if (code === null) {
      code = await _resolveTranslationProvider()
    }
    if (code === null) {
      error.value = 'No translation providers are available for this language pair.'
      return
    }

    isLoading.value = true

    try {
      let res = await translateApi.translate(text, sourceLang.value, targetLang.value, code)

      // Auto-detect conflict: if the detected source equals the target lang,
      // switch to a different target and re-translate (single retry, no history entry for the conflict).
      if (!allowSameLangPair && sourceLang.value === 'auto' && res.detected_lang && res.detected_lang === targetLang.value) {
        targetLang.value = _resolveTargetLangConflict(res.detected_lang)
        res = await translateApi.translate(text, sourceLang.value, targetLang.value, code)
      }

      result.value = res
      _pushToHistory(text, res, code, overrideLexCode, overrideDefCode, overrideCtxCode)
      persistHistory(history.value, historyIndex.value)
    } catch (e: unknown) {
      error.value = extractErrorMessage(e, 'Translation failed')
    } finally {
      isLoading.value = false
    }
  }

  /** Load a word/phrase into the input (e.g. from a clicked definition word) and translate */
  async function translateWord(text: string, srcLang?: string, tgtLang?: string, providerCode: string | null = null) {
    const src = srcLang ?? sourceLang.value
    const tgt = tgtLang ?? targetLang.value
    text = normalizeText(text)

    // If the last history entry already has this exact word + lang pair,
    // just restore it — no need to call the API or push a duplicate entry.
    const last = history.value.length > 0 ? history.value[history.value.length - 1] : null
    if (last && last.sourceText === text && last.sourceLang === src && last.targetLang === tgt) {
      inputText.value = text
      sourceLang.value = src
      targetLang.value = tgt
      result.value = last.result ?? null
      historyIndex.value = history.value.length - 1
      return
    }

    inputText.value = text
    sourceLang.value = src
    targetLang.value = tgt
    await translate(providerCode)
  }

  /** Resolve 'auto' to the detected lang (or fallback) for use as a concrete lang code */
  function _resolvedSourceLang() {
    if (sourceLang.value !== 'auto') return sourceLang.value
    if (result.value?.detected_lang) return result.value.detected_lang
    // Source unknown (auto + no result): pick first enabled lang that differs from current target
    const alt = useLanguageSettingsStore().enabledLangs.find(l => l.code !== targetLang.value)
    return alt?.code ?? targetLang.value
  }

  /** Swap source ↔ target languages only (no input change) */
  function swapLangs() {
    const newTarget = _resolvedSourceLang()
    sourceLang.value = targetLang.value
    targetLang.value = newTarget
  }

  /** Swap source ↔ target languages and put translated text into input.
   *
   * Pass autoTranslate=false to let the caller decide whether to translate
   * (e.g. when the new target lang may be disabled).
   */
  function reverse(autoTranslate = true, providerCode: string | null = null) {
    const newTarget = _resolvedSourceLang()
    sourceLang.value = targetLang.value
    targetLang.value = newTarget
    if (!result.value) return
    inputText.value = result.value.translated_text
    result.value = null
    if (autoTranslate) translate(providerCode)
  }

  /** Navigate backwards in input history */
  function goBack() {
    if (!canGoBack.value) return
    historyIndex.value--
    _restoreFromHistory()
    persistHistory(history.value, historyIndex.value)
  }

  /** Navigate forwards in input history */
  function goForward() {
    if (!canGoForward.value) return
    historyIndex.value++
    _restoreFromHistory()
    persistHistory(history.value, historyIndex.value)
  }

  function _restoreFromHistory() {
    const entry = history.value[historyIndex.value]
    if (!entry) return
    inputText.value = entry.sourceText
    sourceLang.value = entry.sourceLang
    targetLang.value = entry.targetLang
    result.value = entry.result ?? null
    error.value = null
  }

  function saveDefinition(data: Definition | null) {
    const entry = currentEntry.value
    if (entry) {
      entry.definition = data
      persistHistory(history.value, historyIndex.value)
    }
  }

  function saveContextExamples(examples: ContextExample[]) {
    const entry = currentEntry.value
    if (entry) {
      entry.contextExamples = examples
      persistHistory(history.value, historyIndex.value)
    }
  }

  function saveDefProvider(code: string | null) {
    const entry = currentEntry.value
    if (entry) {
      entry.defProviderCode = code
      persistHistory(history.value, historyIndex.value)
    }
  }

  function saveCtxProvider(code: string | null) {
    const entry = currentEntry.value
    if (entry) {
      entry.ctxProviderCode = code
      persistHistory(history.value, historyIndex.value)
    }
  }

  function saveLexicalMatches(matches: string[]) {
    const entry = currentEntry.value
    if (entry) {
      entry.lexicalMatches = matches
      persistHistory(history.value, historyIndex.value)
    }
  }

  function saveLexProvider(code: string | null) {
    const entry = currentEntry.value
    if (entry) {
      entry.lexProviderCode = code
      persistHistory(history.value, historyIndex.value)
    }
  }

  function removeCurrentEntry() {
    if (historyIndex.value < 0 || !history.value.length) return
    history.value.splice(historyIndex.value, 1)
    if (!history.value.length) {
      historyIndex.value = -1
      inputText.value = ''
      result.value = null
      error.value = null
    } else {
      historyIndex.value = Math.min(historyIndex.value, history.value.length - 1)
      _restoreFromHistory()
    }
    persistHistory(history.value, historyIndex.value)
  }

  function clearHistory() {
    history.value = []
    historyIndex.value = -1
    inputText.value = ''
    result.value = null
    error.value = null
    try {
      const key = _storageKey()
      const node = _readNode()
      delete node.history
      if (Object.keys(node).length === 0) {
        localStorage.removeItem(key)
      } else {
        localStorage.setItem(key, JSON.stringify(node))
      }
    } catch {
      localStorage.removeItem(_storageKey())
    }
  }

  function clearResult() {
    result.value = null
    error.value = null
  }

  function reinitialize(userId: number) {
    const stored = loadHistory(userId)
    isLoading.value = false
    error.value = null
    history.value = stored.entries
    historyIndex.value = stored.index
    ctxAllVisible.value = loadCtxAllVisible(userId)
    if (stored.index >= 0 && stored.entries[stored.index]) {
      const e = stored.entries[stored.index]
      inputText.value = e.sourceText
      sourceLang.value = e.sourceLang
      targetLang.value = e.targetLang
      result.value = e.result ?? null
    } else {
      inputText.value = ''
      sourceLang.value = 'auto'
      targetLang.value = ''
      result.value = null
    }
    // Reset after targetLang assignment to avoid the sync watcher capturing
    // the previous user's targetLang as the new user's prevTargetLang.
    prevTargetLang.value = null
  }

  return {
    inputText,
    sourceLang,
    targetLang,
    result,
    isLoading,
    error,
    canGoBack,
    canGoForward,
    currentEntry,
    historyIndex,
    translate,
    translateWord,
    reverse,
    swapLangs,
    goBack,
    goForward,
    clearResult,
    removeCurrentEntry,
    clearHistory,
    saveDefinition,
    saveContextExamples,
    saveDefProvider,
    saveCtxProvider,
    saveLexicalMatches,
    saveLexProvider,
    ctxAllVisible,
    setCtxAllVisible,
    reinitialize,
  }
})
