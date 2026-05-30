export interface User {
  id: number
  username: string
}

export interface Token {
  access_token: string
  token_type: string
}

export interface TranslateResponse {
  translated_text: string
  detected_lang: string | null
  /** Human-readable name of the detected source language (auto-detect only).
   *  Populated by the backend from the full ISO 639-1 reference, available
   *  even when the detected language is not in the user's enabled-lang list. */
  detected_lang_name: string | null
}

export interface WordGroup {
  id: number
  name: string
  position: number
}

export interface WordGroupUpdate {
  name?: string
  position?: number
}

export interface WordbookEntry {
  id: number
  source_lang: string
  target_lang: string
  source_text: string
  target_text: string
  notes?: string
  position: number
  provider_code?: string | null
  /** Computed by backend from provider registry. */
  provider_abbrev?: string | null
  /** Optional color tag; palette defined in `utils/entryColors.ts`. */
  color?: string | null
  group: WordGroup
  created_at: string
  updated_at: string
}

export interface WordbookLookupResult {
  entry_id: number
  group_id: number
  color: string | null
}

export interface WordbookEntryCreate {
  source_lang: string
  target_lang: string
  source_text: string
  target_text: string
  notes?: string
  provider_code?: string | null
}

export interface WordbookEntryUpdate {
  source_text?: string
  target_text?: string
  notes?: string
  position?: number
  provider_code?: string | null
  color?: string | null
}

export interface WordbookMoveItem {
  source_id: number
  target_id: number
}

export interface ContextExample {
  source: string
  target: string
}

export interface Definition {
  word: string
  phonetics: string[]
  meanings: Meaning[]
  source: string
}

export interface Meaning {
  part_of_speech: string
  definitions: DefinitionEntry[]
  synonyms: string[]
}

export interface DefinitionEntry {
  definition: string
  example?: string
  synonyms: string[]
  antonyms: string[]
}

// Translator undo/redo stack entry
export interface TranslatorHistoryEntry {
  sourceText: string
  sourceLang: string
  targetLang: string
  // Only the code identifies a provider; name/abbrev are looked up live from
  // the registry whenever they need to be displayed.
  providerCode?: string
  result?: TranslateResponse
  // undefined = never fetched; null = fetched, not found; object = fetched OK
  definition?: Definition | null
  contextExamples?: ContextExample[]  // undefined = never fetched
  // Lexical matches; undefined = never fetched, array (possibly empty) = fetched OK
  lexicalMatches?: string[]
  // Definition / context / lexical provider last used for this entry
  defProviderCode?: string | null
  ctxProviderCode?: string | null
  lexProviderCode?: string | null
}

export interface Language {
  code: string
  name: string
}

export interface LanguageItem {
  code: string
  name: string
  position: number
  enabled: boolean
}

export interface TtsVoiceItem {
  id: string
  name: string
  /** ISO 639-1 codes that this voice can pronounce. */
  languages: string[]
  position: number
  enabled: boolean
}

export interface ProviderItem {
  code: string
  name: string
  abbrev: string
  position: number
  enabled: boolean
  available: boolean
  unavailable_reason: string | null
  /** Populated for TTS providers only; empty for other capabilities. */
  voices?: TtsVoiceItem[]
}

export interface UserSettings {
  tts: ProviderItem[]
  translation: ProviderItem[]
  definition: ProviderItem[]
  context: ProviderItem[]
  lexical: ProviderItem[]
}
