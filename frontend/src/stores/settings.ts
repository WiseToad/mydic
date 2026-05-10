import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi } from '@/api/settings'
import type { ProviderItem, TtsVoiceItem, UserSettings } from '@/types'

/** All capabilities that have a saved provider preference list. */
export type Capability = 'translation' | 'definition' | 'context' | 'lexical' | 'tts'

/** Per-language preferred TTS voice override.  Lives only in the browser
 *  (localStorage) and never round-trips through the backend; the persistent
 *  source of truth for ordering remains the user's settings. */
interface TtsDefault {
  provider: string
  voice: string
}

/** Namespaced localStorage key for the current user's TTS preferences. */
function _ttsKey(userId?: number): string {
  if (userId !== undefined) return `mydicTts${userId}`
  const raw = localStorage.getItem('mydicUserId')
  const uid = raw !== null ? Number(raw) : NaN
  return !isNaN(uid) ? `mydicTts${uid}` : 'mydicTts'
}

function _loadTtsDefaults(userId?: number): Record<string, TtsDefault> {
  try {
    const raw = localStorage.getItem(_ttsKey(userId))
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    const out: Record<string, TtsDefault> = {}
    for (const [lang, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (
        value && typeof value === 'object'
        && typeof (value as TtsDefault).provider === 'string'
        && typeof (value as TtsDefault).voice === 'string'
      ) {
        out[lang] = {
          provider: (value as TtsDefault).provider,
          voice: (value as TtsDefault).voice,
        }
      }
    }
    return out
  } catch {
    return {}
  }
}

function _saveTtsDefaults(map: Record<string, TtsDefault>) {
  const key = _ttsKey()
  try {
    localStorage.setItem(key, JSON.stringify(map))
  } catch {
    // Quota exhausted or storage disabled; drop the cached pick rather than
    // crashing playback - the next click will fall back to the ordered list.
    try { localStorage.removeItem(key) } catch { /* ignore */ }
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const loaded = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const saveCount = ref(0)

  const tts = ref<ProviderItem[]>([])
  const translation = ref<ProviderItem[]>([])
  const definition = ref<ProviderItem[]>([])
  const context = ref<ProviderItem[]>([])
  const lexical = ref<ProviderItem[]>([])

  /** Browser-local lang -> (provider, voice) map; populated by long-press
   *  popup picks.  Consulted by ``defaultTtsForLang`` before the ordered
   *  list, and silently ignored when the stored pair is no longer enabled
   *  / available so the user never gets stranded with a stale choice. */
  const ttsDefaultsByLang = ref<Record<string, TtsDefault>>(_loadTtsDefaults())

  /** Flat (provider, voice) pairs from TTS prefs that support `lang`,
   *  in user-preference order, restricted to enabled+available combos.
   *  Used by the audio-button long-press popup. */
  function ttsChoicesForLang(lang: string): Array<{
    provider: ProviderItem
    voice: TtsVoiceItem
  }> {
    const out: Array<{ provider: ProviderItem; voice: TtsVoiceItem }> = []
    for (const provider of tts.value) {
      if (!provider.enabled || !provider.available) continue
      const voices = provider.voices ?? []
      for (const voice of voices) {
        if (!voice.enabled) continue
        // No declared languages -> treat as universal (popup still shows it).
        if (voice.languages.length === 0 || voice.languages.includes(lang)) {
          out.push({ provider, voice })
        }
      }
    }
    return out
  }

  /** Resolve the default (provider, voice) for a normal click on the audio
   *  button.  Honours the user's per-lang pick from the long-press popup
   *  when it's still enabled+available; otherwise falls back to the first
   *  match in their settings-defined order. */
  function defaultTtsForLang(lang: string): {
    provider: ProviderItem
    voice: TtsVoiceItem
  } | null {
    const choices = ttsChoicesForLang(lang)
    if (choices.length === 0) return null
    const pick = ttsDefaultsByLang.value[lang]
    if (pick) {
      const match = choices.find(
        (c) => c.provider.code === pick.provider && c.voice.id === pick.voice,
      )
      if (match) return match
    }
    return choices[0]
  }

  /** Record (providerCode, voiceId) as the default for ``lang`` going
   *  forward.  The choice is browser-local and persists across reloads via
   *  localStorage; it does not modify the user's voice ordering. */
  function setDefaultTtsForLang(
    lang: string,
    providerCode: string,
    voiceId: string,
  ) {
    ttsDefaultsByLang.value = {
      ...ttsDefaultsByLang.value,
      [lang]: { provider: providerCode, voice: voiceId },
    }
    _saveTtsDefaults(ttsDefaultsByLang.value)
  }

  function _list(cap: Capability): ProviderItem[] {
    if (cap === 'translation') return translation.value
    if (cap === 'definition') return definition.value
    if (cap === 'context') return context.value
    if (cap === 'lexical') return lexical.value
    return tts.value
  }

  function _setList(cap: Capability, items: ProviderItem[]) {
    if (cap === 'translation') translation.value = items
    else if (cap === 'definition') definition.value = items
    else if (cap === 'context') context.value = items
    else if (cap === 'lexical') lexical.value = items
    else tts.value = items
  }

  function _normalizePositions(items: ProviderItem[]): ProviderItem[] {
    return items.map((p, i) => ({ ...p, position: i }))
  }

  function _normalizeVoicePositions(voices: TtsVoiceItem[]): TtsVoiceItem[] {
    return voices.map((v, i) => ({ ...v, position: i }))
  }

  function _applySettings(data: UserSettings) {
    tts.value = data.tts
    translation.value = data.translation
    definition.value = data.definition
    context.value = data.context
    lexical.value = data.lexical
    loaded.value = true
    error.value = null
  }

  async function load() {
    if (loaded.value) return
    try {
      const data = await settingsApi.getSettings()
      _applySettings(data)
    } catch (e: unknown) {
      error.value = 'Failed to load settings'
    }
  }

  async function save() {
    saving.value = true
    error.value = null
    try {
      const data = await settingsApi.saveSettings({
        tts: tts.value,
        translation: translation.value,
        definition: definition.value,
        context: context.value,
        lexical: lexical.value,
      })
      _applySettings(data)
      // Components that own provider lists watch `saveCount` and refetch on bump.
      saveCount.value++
    } catch (e: unknown) {
      error.value = 'Failed to save settings'
    } finally {
      saving.value = false
    }
  }

  function moveUp(cap: Capability, index: number) {
    if (index <= 0) return
    const list = [..._list(cap)]
    ;[list[index - 1], list[index]] = [list[index], list[index - 1]]
    _setList(cap, _normalizePositions(list))
  }

  function moveDown(cap: Capability, index: number) {
    const list = _list(cap)
    if (index >= list.length - 1) return
    const copy = [...list]
    ;[copy[index], copy[index + 1]] = [copy[index + 1], copy[index]]
    _setList(cap, _normalizePositions(copy))
  }

  function toggleEnabled(cap: Capability, index: number) {
    const list = _list(cap)
    const copy = list.map((item, i) =>
      i === index ? { ...item, enabled: !item.enabled } : item
    )
    _setList(cap, copy)
  }

  function reorder(cap: Capability, from: number, to: number) {
    const list = [..._list(cap)]
    const [item] = list.splice(from, 1)
    list.splice(to, 0, item)
    _setList(cap, _normalizePositions(list))
  }

  // ---------------------------------------------------------------------
  // TTS voice-level helpers (nested under each TTS provider)
  // ---------------------------------------------------------------------

  function _withVoices(
    providerIndex: number,
    update: (voices: TtsVoiceItem[]) => TtsVoiceItem[],
  ) {
    const provider = tts.value[providerIndex]
    if (!provider) return
    const voices = provider.voices ?? []
    const next = _normalizeVoicePositions(update([...voices]))
    tts.value = tts.value.map((p, i) =>
      i === providerIndex ? { ...p, voices: next } : p,
    )
  }

  function toggleVoiceEnabled(providerIndex: number, voiceIndex: number) {
    _withVoices(providerIndex, (voices) =>
      voices.map((v, i) => (i === voiceIndex ? { ...v, enabled: !v.enabled } : v)),
    )
  }

  function reorderVoice(providerIndex: number, from: number, to: number) {
    _withVoices(providerIndex, (voices) => {
      const [item] = voices.splice(from, 1)
      voices.splice(to, 0, item)
      return voices
    })
  }

  function reinitialize(userId: number) {
    loaded.value = false
    saving.value = false
    error.value = null
    saveCount.value = 0
    tts.value = []
    translation.value = []
    definition.value = []
    context.value = []
    lexical.value = []
    ttsDefaultsByLang.value = _loadTtsDefaults(userId)
  }

  return {
    loaded,
    saving,
    error,
    saveCount,
    tts,
    translation,
    definition,
    context,
    lexical,
    load,
    save,
    moveUp,
    moveDown,
    toggleEnabled,
    reorder,
    toggleVoiceEnabled,
    reorderVoice,
    ttsChoicesForLang,
    defaultTtsForLang,
    setDefaultTtsForLang,
    reinitialize,
  }
})
