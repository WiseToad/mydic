import { getTtsSamples } from '@/api/tts'

/**
 * Sample sentences per ISO 639-1 language, loaded lazily from
 * `GET /tts/samples` on first call to `ensureTtsSamplesLoaded()`.
 * Covers all languages supported by at least one configured TTS provider.
 */
let _cache: Record<string, string> | null = null
let _loading: Promise<void> | null = null

/**
 * Pre-fetch sample sentences from the backend and cache them.
 * Safe to call multiple times — only one request is ever in flight.
 * Call this in `onMounted` of views that use `ttsSampleFor`.
 */
export async function ensureTtsSamplesLoaded(): Promise<void> {
  if (_cache !== null) return
  if (_loading !== null) return _loading
  _loading = getTtsSamples()
    .then((data) => { _cache = data })
    .catch(() => { _cache = {} })  // on failure, cache empty map so we fall back gracefully
    .finally(() => { _loading = null })
  return _loading
}

/**
 * Return a short sample sentence for *lang* (ISO 639-1 code).
 * Returns from the backend-loaded cache when available; falls back to a
 * generic English sentence so the voice preview always produces something
 * audible even before the cache is populated.
 */
export function ttsSampleFor(lang: string): string {
  return _cache?.[lang.toLowerCase()] ?? ``
}
