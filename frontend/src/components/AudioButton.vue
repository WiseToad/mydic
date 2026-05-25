<template>
  <div v-if="!settings.loaded || choices.length > 0" class="relative inline-flex" ref="rootRef" data-audio-button draggable="false">
    <button
      :title="buttonTitle"
      :disabled="!text"
      :class="[
        'inline-flex items-center justify-center rounded-full disabled:opacity-30 disabled:cursor-not-allowed touch-none',
        isPlaying ? '' : 'transition-colors',
        size === 'sm' ? 'w-6 h-6' : 'w-8 h-8',
        isGenerating
          ? 'text-gray-400 hover:text-gray-300'
          : isPlaying
            ? 'text-red-400 hover:text-red-300 hover:bg-red-500/10'
            : isSlow
              ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/10'
              : 'text-gray-500 hover:text-primary-400 hover:bg-primary-500/10'
      ]"
      @click.stop="onClick"
      @touchstart.prevent
      @pointerdown.stop.prevent="onPointerDown"
      @pointerup.stop="onPointerUp"
      @pointerleave="onPointerUp"
      @pointercancel="onPointerUp"
      @contextmenu.prevent
    >
      <!-- Spinner while server is generating audio -->
      <svg v-if="isGenerating" xmlns="http://www.w3.org/2000/svg" :class="['animate-spin', size === 'sm' ? 'w-4 h-4' : 'w-5 h-5']" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
      </svg>
      <!-- Stop icon when playing -->
      <svg v-else-if="isPlaying" xmlns="http://www.w3.org/2000/svg" :class="size === 'sm' ? 'w-4 h-4' : 'w-5 h-5'" viewBox="0 0 24 24" fill="currentColor">
        <path d="M6 6h12v12H6z"/>
      </svg>
      <!-- Speaker icon when idle (color shifts to amber while in slow-on-repeat mode). -->
      <svg v-else xmlns="http://www.w3.org/2000/svg" :class="size === 'sm' ? 'w-4 h-4' : 'w-5 h-5'" viewBox="0 0 24 24" fill="currentColor">
        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
      </svg>
    </button>

    <!-- Long-press popup: flat list of (provider · voice) for the button's lang -->
    <Teleport to="body">
      <div
        v-if="popupVisible"
        ref="popupRef"
        data-audio-popup
        :style="{ left: popupLeft + 'px', top: popupTop + 'px' }"
        class="fixed z-50 max-h-72 bg-surface-900 border border-surface-700 rounded-lg shadow-2xl min-w-[180px] flex flex-col"
        @pointerdown.stop
        @click.stop
      >
        <p class="px-3 pt-1 pb-0.5 text-xs text-gray-500 font-semibold uppercase tracking-wide shrink-0">Select voice</p>
        <div class="overflow-auto py-1">
          <div v-if="choices.length === 0" class="px-3 py-2 text-xs text-gray-500">
            No TTS voices available for this language.
          </div>
          <button
            v-for="c in choices"
            :key="c.provider.code + ':' + c.voice.id"
            type="button"
            class="w-full text-left px-3 py-1.5 text-sm transition-colors flex items-center gap-2"
            :class="isCurrentDefault(c)
              ? 'text-primary-300 bg-primary-500/10 hover:bg-primary-500/15'
              : 'text-gray-200 hover:bg-surface-700'"
            :title="isCurrentDefault(c) ? 'Current default voice' : undefined"
            @click="onChoosePopup(c.provider.code, c.voice.id)"
          >
            <!--
              The current default for this lang gets a leading check so the
              highlight is unambiguous (the bg tint alone could be misread as
              a focus/hover style on touch devices).
            -->
            <svg
              v-if="isCurrentDefault(c)"
              xmlns="http://www.w3.org/2000/svg"
              class="w-3.5 h-3.5 text-primary-400 shrink-0"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>
            <span class="w-3.5 h-3.5 shrink-0" v-else aria-hidden="true" />
            <span
              class="text-xs uppercase shrink-0"
              :class="isCurrentDefault(c) ? 'text-primary-300' : 'text-primary-400'"
            >{{ c.provider.abbrev || c.provider.code }}</span>
            <span class="truncate">{{ c.voice.name || c.voice.id }}</span>
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onDeactivated, ref } from 'vue'
import {
  claimSlow,
  clearSlow,
  isSlowOwner,
  playTts,
  stopTts,
  type PlaybackResult,
  type TtsSpeed,
} from '@/api/tts'
import { useSettingsStore } from '@/stores/settings'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/utils/error'
import type { ProviderItem, TtsVoiceItem } from '@/types'

const props = withDefaults(defineProps<{
  text: string
  lang: string
  title?: string
  size?: 'sm' | 'md'
}>(), { title: 'Listen', size: 'md' })

/** Time the user must hold the button before the voice-picker popup opens. */
const LONG_PRESS_MS = 500

/** Per-instance identity used as the slow-mode owner key.  Stable for the
 *  lifetime of this AudioButton; never collides with another instance. */
const buttonId = Symbol('AudioButton')

const settings = useSettingsStore()
const toast = useToastStore()

const rootRef = ref<HTMLElement | null>(null)
const popupRef = ref<HTMLElement | null>(null)
const isPlaying = ref(false)
const isGenerating = ref(false)

/** Whether a TTS request is currently in-flight.  Set immediately (unlike
 *  `isGenerating` which is delayed) so concurrent clicks are blocked and
 *  unmount teardown can stop a pending request. */
let _inFlight = false
/** Timer that delays the spinner; cancelled when audio starts before the
 *  delay expires so the spinner never appears for fast/cached responses. */
let _spinnerTimer: ReturnType<typeof setTimeout> | null = null
function _cancelSpinnerTimer() {
  if (_spinnerTimer !== null) { clearTimeout(_spinnerTimer); _spinnerTimer = null }
}

const popupVisible = ref(false)
const popupLeft = ref(0)
const popupTop = ref(0)

let pressTimer: ReturnType<typeof setTimeout> | null = null
let longPressFired = false
let _longPressPointerId: number | null = null

// One-shot guard: after a long-press opens the popup, releasing the finger
// anywhere may synthesize a spurious click on whatever element is under the
// pointer at that moment.  We intercept that click (capture phase, before any
// child handler) and swallow it unless it lands inside the popup itself.
let _longPressClickGuard: ((e: MouseEvent) => void) | null = null

// One-shot pointerup / pointercancel guard for the same press that opened the
// popup.  On desktop, releasing the held mouse button over another element
// fires pointerup on that element and triggers side-effects there (e.g.
// WordbookEntry's onCardPointerUpCapture which focuses a card).  We intercept
// that specific pointerup in the capture phase and stop propagation so it
// reaches no element handler.  Keyed by pointerId so it never fires for an
// unrelated touch or mouse button.
let _longPressPointerUpGuard: ((e: PointerEvent) => void) | null = null

function _registerLongPressClickGuard() {
  _cleanLongPressClickGuard()
  const handler = (e: MouseEvent) => {
    document.removeEventListener('click', handler, true)
    _longPressClickGuard = null
    if ((e.target as Element | null)?.closest('[data-audio-popup]')) return
    e.stopPropagation()
    e.preventDefault()
  }
  _longPressClickGuard = handler
  document.addEventListener('click', handler, true)
}

function _cleanLongPressClickGuard() {
  if (_longPressClickGuard) {
    document.removeEventListener('click', _longPressClickGuard, true)
    _longPressClickGuard = null
  }
}

function _registerLongPressPointerUpGuard() {
  _cleanLongPressPointerUpGuard()
  const id = _longPressPointerId
  if (id === null) return
  const handler = (e: PointerEvent) => {
    if (e.pointerId !== id) return
    _cleanLongPressPointerUpGuard()
    // On pointerup: stop propagation so no element below sees this event
    // (prevents onCardPointerUpCapture and similar handlers from firing).
    // On pointercancel: just clean up — cancels cause no side-effects.
    if (e.type === 'pointerup') e.stopPropagation()
  }
  _longPressPointerUpGuard = handler
  document.addEventListener('pointerup', handler, true)
  document.addEventListener('pointercancel', handler, true)
}

function _cleanLongPressPointerUpGuard() {
  if (_longPressPointerUpGuard) {
    document.removeEventListener('pointerup', _longPressPointerUpGuard, true)
    document.removeEventListener('pointercancel', _longPressPointerUpGuard, true)
    _longPressPointerUpGuard = null
  }
}

/** Reactive: this button is currently "primed for slow on next click". */
const isSlow = computed(() => isSlowOwner(buttonId))

const choices = computed(() => settings.ttsChoicesForLang(props.lang))

/**
 * Reactive (provider, voice) pair the user has previously picked from this
 * lang's popup, or the natural fallback when no pick exists.  Compared by
 * identity (provider.code + voice.id) against each row in the popup so the
 * current default gets a clear visual marker.
 */
const currentDefault = computed(() => settings.defaultTtsForLang(props.lang))

function isCurrentDefault(choice: { provider: ProviderItem; voice: TtsVoiceItem }): boolean {
  const def = currentDefault.value
  if (!def) return false
  return def.provider.code === choice.provider.code && def.voice.id === choice.voice.id
}

const buttonTitle = computed(() => {
  if (isGenerating.value) return 'Generating… (click to cancel)'
  if (isPlaying.value) return 'Stop'
  return isSlow.value ? `${props.title} (slow)` : props.title
})

function _resolvedDefault() {
  return settings.defaultTtsForLang(props.lang)
}

/** Drive a single playback request through the slow-state machine.
 *
 *  Speed selection (no explicit override):
 *    - This button is the slow owner       → SLOW
 *    - Otherwise                            → NORMAL (and any other button's
 *      slow ownership is cleared first, satisfying #5)
 *
 *  Post-playback transitions:
 *    - speed=NORMAL & result='completed'    → claim slow ownership (#1)
 *    - speed=NORMAL & result='interrupted'  → stay normal (don't promote
 *      partial playback to slow)
 *    - speed=SLOW   & any result            → always release slow ownership
 *      (interrupted or not, per spec)
 */
async function _play(
  override?: { provider: string; voice: string; forceSpeed?: TtsSpeed },
) {
  if (!props.text) return
  if (isPlaying.value || _inFlight) {
    stopTts()
    return
  }

  const wasSlow = isSlowOwner(buttonId)
  const speed: TtsSpeed = override?.forceSpeed ?? (wasSlow ? 'SLOW' : 'NORMAL')

  // #5: a normal-speed playback elsewhere immediately clears any other
  // button's slow ownership.  When playing slow on the current owner, keep
  // the ownership marker until the playback finishes so the post-playback
  // branch below can release it.
  if (speed !== 'SLOW' || !wasSlow) {
    clearSlow()
  }

  const fallback = _resolvedDefault()
  if (!fallback && !override) return  // no voices available for this lang — bail out silently
  const resolvedProvider = override?.provider ?? fallback?.provider.code
  const resolvedVoice = override?.voice ?? fallback?.voice.id
  // After the guard above at least one source is non-null, but TypeScript
  // cannot infer that, so we narrow explicitly.
  if (!resolvedProvider) return

  _inFlight = true
  // Delay spinner to avoid flicker for fast / cached responses.
  _spinnerTimer = setTimeout(() => {
    _spinnerTimer = null
    if (_inFlight) isGenerating.value = true
  }, 200)
  let result: PlaybackResult
  try {
    result = await playTts(
      props.text, props.lang,
      { speed, provider: resolvedProvider, voice: resolvedVoice },
      () => {
        // Audio has started — cancel pending spinner and switch to stop-button.
        _cancelSpinnerTimer()
        isGenerating.value = false
        isPlaying.value = true
      },
    )
  } catch (e: unknown) {
    _cancelSpinnerTimer()
    toast.error(extractErrorMessage(e, 'Could not play audio'))
    return
  } finally {
    _cancelSpinnerTimer()
    _inFlight = false
    isGenerating.value = false
    isPlaying.value = false
  }

  if (speed === 'SLOW') {
    // Always end slow mode after a slow playback (#1).
    clearSlow()
  } else if (result === 'completed') {
    // Only enter slow mode after an uninterrupted normal playback (#1).
    claimSlow(buttonId)
  }
  // speed=NORMAL & interrupted: stay normal (no claim).
}

function onPointerDown(e: PointerEvent) {
  // Only start long-press on the primary button.
  if (e.button !== 0) return
  _longPressPointerId = e.pointerId
  longPressFired = false
  if (pressTimer) clearTimeout(pressTimer)
  pressTimer = setTimeout(() => {
    longPressFired = true
    pressTimer = null
    openPopup()
  }, LONG_PRESS_MS)
}

function onPointerUp() {
  if (pressTimer) {
    clearTimeout(pressTimer)
    pressTimer = null
  }
}

function onClick() {
  if (longPressFired) {
    longPressFired = false
    return
  }
  void _play()
}

/**
 * Open the long-press popup and place it relative to the audio button with
 * viewport-edge awareness:
 *  - Default placement is below the button, left-aligned to it.
 *  - When the popup would overflow the bottom edge of the viewport, it
 *    flips up so its bottom sits just above the button (#4).
 *  - When the popup would overflow the right edge, it switches to being
 *    right-aligned to the audio button instead of left-aligned (#5).
 *
 * Initial position is computed from the button rect alone (no popup size yet),
 * then refined after `nextTick` once the popup has rendered and we can read
 * its actual size.  This two-pass approach avoids placing the popup off-screen
 * for one frame on slower machines.
 */
function openPopup() {
  if (!rootRef.value || !props.text) return
  // Clear any text selection the browser started during the long-press hold.
  // On Android, a long press can select adjacent text before our timer fires;
  // discarding it here ensures only the voice picker is shown.
  window.getSelection()?.removeAllRanges()
  const rect = rootRef.value.getBoundingClientRect()
  // First-pass guess (good enough until the popup measures itself).
  popupLeft.value = Math.max(8, Math.min(window.innerWidth - 200, rect.left))
  popupTop.value = rect.bottom + 4
  popupVisible.value = true
  // Stop any current playback so the next one is the user's chosen voice.
  stopTts()
  document.addEventListener('pointerdown', onOutsidePointerDown, true)
  document.addEventListener('dragstart', onDocumentDragStart, true)
  // Swallow the click that follows releasing the long-press finger, unless
  // it lands inside the popup (where the user is making a deliberate choice).
  _registerLongPressClickGuard()
  // Swallow the pointerup that ends the long-press gesture so it cannot
  // trigger side-effects on whatever element the pointer happens to be over
  // at the moment of release (e.g. focusing a different wordbook card).
  _registerLongPressPointerUpGuard()
  // Second-pass refinement: now that the popup is in the DOM, measure it
  // and apply viewport-aware adjustments.
  void nextTick(() => positionPopup(rect))
}

/** Reposition the rendered popup so it stays inside the viewport. */
function positionPopup(buttonRect: DOMRect) {
  const popup = popupRef.value
  if (!popup) return
  const popupRect = popup.getBoundingClientRect()
  const popupHeight = popupRect.height
  const popupWidth = popupRect.width
  const margin = 4

  // Vertical: prefer below; flip above when below would overflow AND there
  // is at least as much space above the button.
  const spaceBelow = window.innerHeight - buttonRect.bottom
  const spaceAbove = buttonRect.top
  if (spaceBelow < popupHeight + margin && spaceAbove > spaceBelow) {
    popupTop.value = Math.max(margin, buttonRect.top - popupHeight - margin)
  } else {
    popupTop.value = buttonRect.bottom + margin
  }

  // Horizontal: prefer left-aligned to the button; flip to right-aligned
  // when the popup would otherwise clip the viewport's right edge.
  if (buttonRect.left + popupWidth + margin > window.innerWidth) {
    popupLeft.value = Math.max(margin, buttonRect.right - popupWidth)
  } else {
    popupLeft.value = Math.max(margin, buttonRect.left)
  }
}

function onOutsidePointerDown(e: PointerEvent) {
  // The handler is registered in the capture phase so it runs before any
  // listener inside the popup.  Bail out for clicks that originate inside
  // the popup itself; otherwise the popup would be torn down before the
  // chosen item's @click handler ever fires.
  if (popupRef.value && popupRef.value.contains(e.target as Node)) return
  popupVisible.value = false
  document.removeEventListener('pointerdown', onOutsidePointerDown, true)
  document.removeEventListener('dragstart', onDocumentDragStart, true)
  // Don't fire a normal click after long-press dismissal.
  e.stopPropagation()
}

/** Close the voice popup when any HTML5 card drag starts. */
function onDocumentDragStart() {
  popupVisible.value = false
  document.removeEventListener('pointerdown', onOutsidePointerDown, true)
  document.removeEventListener('dragstart', onDocumentDragStart, true)
}

function onChoosePopup(providerCode: string, voiceId: string) {
  popupVisible.value = false
  document.removeEventListener('pointerdown', onOutsidePointerDown, true)
  document.removeEventListener('dragstart', onDocumentDragStart, true)
  // Picking a voice from the popup also records it as the default for this
  // button's language (browser-local), so future plain clicks default to
  // the same voice without altering the user's settings-defined order.
  settings.setDefaultTtsForLang(props.lang, providerCode, voiceId)
  // #9: popup picks unconditionally start a NORMAL-speed playback, even if
  // this button currently owns slow mode.
  void _play({ provider: providerCode, voice: voiceId, forceSpeed: 'NORMAL' })
}

// When the parent KeepAlive view is navigated away from, the component is
// deactivated (not destroyed). Teleported popups stay in <body> in that case,
// so we must close them explicitly.
onDeactivated(() => {
  _cleanLongPressClickGuard()
  _cleanLongPressPointerUpGuard()
  if (popupVisible.value) {
    popupVisible.value = false
    document.removeEventListener('pointerdown', onOutsidePointerDown, true)
    document.removeEventListener('dragstart', onDocumentDragStart, true)
  }
  if (pressTimer) {
    clearTimeout(pressTimer)
    pressTimer = null
  }
})

onBeforeUnmount(() => {
  if (pressTimer) clearTimeout(pressTimer)
  _cancelSpinnerTimer()
  _cleanLongPressClickGuard()
  _cleanLongPressPointerUpGuard()
  document.removeEventListener('pointerdown', onOutsidePointerDown, true)
  document.removeEventListener('dragstart', onDocumentDragStart, true)
  // #4: a button being unmounted (e.g. wordbook card filtered out) must
  // stop any playback it initiated and release any slow ownership it held.
  if (isPlaying.value || _inFlight) stopTts()
  if (isSlowOwner(buttonId)) clearSlow()
})
</script>
