import { ref } from 'vue'
import { apiClient } from './client'

export async function getTtsSamples(): Promise<Record<string, string>> {
  const { data } = await apiClient.get<Record<string, string>>('/tts/samples')
  return data
}

/** Discrete pronunciation speed matching the backend's `TtsSpeed` enum. */
export type TtsSpeed = 'NORMAL' | 'SLOW'

/** Outcome of a single playTts call.
 *  - ``completed``: the audio reached its natural end (``onended`` fired).
 *  - ``interrupted``: playback was stopped externally (e.g. another button
 *    started, the component unmounted, or the user clicked the same button
 *    to stop).  Distinct from playback errors which still reject. */
export type PlaybackResult = 'completed' | 'interrupted'

/** Parameters for a TTS request.  *provider* selects the TTS engine and is
 *  required; *voice* is optional and, when omitted, is resolved by the backend
 *  from the user's saved preferences for the given provider and language. */
export interface TtsOptions {
  speed?: TtsSpeed
  provider: string
  voice?: string
}

/** How long the slow-on-repeat affordance stays armed after a successful
 *  normal-speed playback ends.  Kept in sync with the user-facing UX spec. */
const SLOW_RESET_MS = 3000

// ---------------------------------------------------------------------------
// Slow-on-repeat singleton
//
// At most one AudioButton instance can be "primed for slow" at any moment
// (#5: starting playback elsewhere immediately resets it).  The state lives
// here as a module-level ref so all AudioButton instances see updates
// reactively, and a setTimeout drives the auto-decay (#2: stable state for
// NORMAL, time-bounded for SLOW).
// ---------------------------------------------------------------------------

const _slowOwner = ref<symbol | null>(null)
let _slowResetTimer: ReturnType<typeof setTimeout> | null = null

/** True when *id* is currently the slow-mode owner. */
export function isSlowOwner(id: symbol): boolean {
  return _slowOwner.value === id
}

/** Mark *id* as the slow-mode owner; resets after ``SLOW_RESET_MS`` if no
 *  one re-claims or clears it first.  Replaces any previous owner. */
export function claimSlow(id: symbol): void {
  if (_slowResetTimer !== null) {
    clearTimeout(_slowResetTimer)
    _slowResetTimer = null
  }
  _slowOwner.value = id
  _slowResetTimer = setTimeout(() => {
    _slowResetTimer = null
    if (_slowOwner.value === id) _slowOwner.value = null
  }, SLOW_RESET_MS)
}

/** Drop slow-mode ownership immediately (cancelling the auto-decay timer). */
export function clearSlow(): void {
  if (_slowResetTimer !== null) {
    clearTimeout(_slowResetTimer)
    _slowResetTimer = null
  }
  _slowOwner.value = null
}

// ---------------------------------------------------------------------------
// Playback singleton
// ---------------------------------------------------------------------------

let _abortController: AbortController | null = null
let _audio: HTMLAudioElement | null = null
let _blobUrl: string | null = null
/** Called by :func:`_stopCurrent` to settle the in-flight playTts promise
 *  with ``'interrupted'`` when external code stops the audio. */
let _resolveInterrupt: (() => void) | null = null

function _stopCurrent() {
  if (_abortController) {
    _abortController.abort()
    _abortController = null
  }
  if (_audio) {
    _audio.pause()
    _audio.onended = null
    _audio.onerror = null
    _audio = null
  }
  if (_blobUrl) {
    URL.revokeObjectURL(_blobUrl)
    _blobUrl = null
  }
  // Settle the previous caller's promise so its isPlaying resets and the
  // caller's post-playback bookkeeping (slow-state transitions) runs with
  // an accurate ``'interrupted'`` outcome.
  _resolveInterrupt?.()
  _resolveInterrupt = null
}

/**
 * Fetch TTS audio for `text` in `lang` and return a blob URL.
 * The caller is responsible for calling URL.revokeObjectURL() after playback.
 */
export async function fetchTtsUrl(
  text: string,
  lang: string,
  options: TtsOptions,
  signal?: AbortSignal,
): Promise<string> {
  const params: Record<string, string> = {
    text,
    lang,
    speed: options.speed ?? 'NORMAL',
    provider: options.provider,
  }
  if (options.voice) params.voice = options.voice
  const { data } = await apiClient.get('/tts', {
    params,
    responseType: 'blob',
    signal,
  })
  return URL.createObjectURL(data as Blob)
}

/** Stop any currently playing audio.  Safe to call when nothing is playing. */
export function stopTts(): void {
  _stopCurrent()
}

/**
 * Play TTS audio. Stops any currently playing audio first.
 * Resolves with ``'completed'`` when the audio reaches its natural end,
 * or ``'interrupted'`` when stopped externally.  Rejects on fetch / playback
 * errors so the caller can surface a toast.
 *
 * @param onPlaybackStarted  Optional callback invoked the moment audio
 *   playback actually begins (i.e. after the server-side synthesis is done
 *   and the browser starts playing).  Useful for transitioning spinner →
 *   stop-button indicators in the caller.
 */
export async function playTts(
  text: string,
  lang: string,
  options: TtsOptions,
  onPlaybackStarted?: () => void,
): Promise<PlaybackResult> {
  _stopCurrent()

  if (!text) {
    return 'interrupted'
  }

  const controller = new AbortController()
  _abortController = controller

  let url: string
  try {
    url = await fetchTtsUrl(text, lang, options, controller.signal)
  } catch {
    if (controller.signal.aborted) return 'interrupted'
    throw new Error('Could not fetch audio')
  }

  if (controller.signal.aborted) {
    URL.revokeObjectURL(url)
    return 'interrupted'
  }

  _abortController = null
  _blobUrl = url
  const audio = new Audio(url)
  _audio = audio

  return new Promise<PlaybackResult>((resolve, reject) => {
    let settled = false
    const cleanup = () => {
      URL.revokeObjectURL(url)
      if (_blobUrl === url) _blobUrl = null
      if (_audio === audio) _audio = null
      if (_resolveInterrupt === interruptHandler) _resolveInterrupt = null
    }
    const settleOk = (result: PlaybackResult) => {
      if (settled) return
      settled = true
      cleanup()
      resolve(result)
    }
    const settleError = (err: Error) => {
      if (settled) return
      settled = true
      cleanup()
      reject(err)
    }
    const interruptHandler = () => settleOk('interrupted')
    _resolveInterrupt = interruptHandler

    audio.onended = () => settleOk('completed')
    audio.onerror = () => settleError(new Error('Audio playback failed'))
    const playPromise = audio.play()
    playPromise.then(() => onPlaybackStarted?.()).catch((e) => settleError(e instanceof Error ? e : new Error(String(e))))
  })
}
