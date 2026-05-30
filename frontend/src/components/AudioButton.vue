<template>
  <div v-if="!settings.loaded || choices.length > 0" class="relative inline-flex" ref="rootRef" data-audio-button draggable="false">
    <button
      :title="buttonTitle"
      :disabled="!text"
      :class="[
        'inline-flex items-center justify-center rounded-full disabled:opacity-30 disabled:cursor-not-allowed touch-none',
        isPlaying ? '' : 'transition-colors',
        size === 'sm' ? 'w-7 h-7' : 'w-8 h-8',
        isGenerating
          ? 'text-gray-400 hover:text-gray-300'
          : isPlaying
            ? 'text-red-400 hover:text-red-300 hover:bg-red-500/10'
            : isSlow
              ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/10'
              : 'text-gray-500 hover:text-primary-400 hover:bg-primary-500/10'
      ]"
      @click.stop
      @pointerdown.stop.prevent="onPointerDown"
      @pointerup.stop="onPointerUp"
      @pointerleave="cancelPress"
      @pointercancel="cancelPress"
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
        <div ref="popupScrollRef" class="overflow-auto py-1">
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
            :data-selected="isCurrentDefault(c) || undefined"
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
import { computed, nextTick, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { useLongPress } from '@/composables/useLongPress'
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
import { SPINNER_DELAY_MS } from '@/utils/ui'
import type { ProviderItem, TtsVoiceItem } from '@/types'

const props = withDefaults(defineProps<{
  text: string
  lang: string
  title?: string
  size?: 'sm' | 'md'
}>(), { title: 'Listen', size: 'md' })

const emit = defineEmits<{
  (e: 'longpress'): void
}>()

const buttonId = Symbol('AudioButton')

const settings = useSettingsStore()
const toast = useToastStore()

const rootRef = ref<HTMLElement | null>(null)
const popupRef = ref<HTMLElement | null>(null)
const popupScrollRef = ref<HTMLElement | null>(null)
const isPlaying = ref(false)
const isGenerating = ref(false)

/** Set immediately (unlike the delayed `isGenerating`) to block concurrent requests. */
let _inFlight = false
/** Delayed spinner timer — cancelled if audio starts before it fires, preventing flicker. */
let _spinnerTimer: ReturnType<typeof setTimeout> | null = null
function _cancelSpinnerTimer() {
  if (_spinnerTimer !== null) { clearTimeout(_spinnerTimer); _spinnerTimer = null }
}

const popupVisible = ref(false)
const popupLeft = ref(0)
const popupTop = ref(0)

let _longPressPointerId: number | null = null

// One-shot guard: intercepts the pointerup that ends the long-press gesture so
// it cannot focus a different wordbook card.  Keyed by pointerId.
let _longPressPointerUpGuard: ((e: PointerEvent) => void) | null = null

function _registerLongPressPointerUpGuard() {
  _cleanLongPressPointerUpGuard()
  const id = _longPressPointerId
  if (id === null) return
  const handler = (e: PointerEvent) => {
    if (e.pointerId !== id) return
    _cleanLongPressPointerUpGuard()
    // pointerup: stop propagation to prevent other cards from being focused.
    // pointercancel: just clean up.
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

/** User-picked (or fallback) voice for this lang; used to mark the current default in the popup. */
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

/** Plays TTS through the slow-mode state machine.
 *  NORMAL + completed → claim slow; NORMAL + interrupted → stay normal; SLOW → always release.
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

  // Normal-speed play clears any other button's slow ownership.
  // Slow play: keep ownership until playback finishes so we can release it below.
  if (speed !== 'SLOW' || !wasSlow) {
    clearSlow()
  }

  const fallback = currentDefault.value
  if (!fallback && !override) return  // no voices available for this lang — bail out silently
  const resolvedProvider = override?.provider ?? fallback?.provider.code
  const resolvedVoice = override?.voice ?? fallback?.voice.id
  // TypeScript can't infer non-null here; narrow explicitly.
  if (!resolvedProvider) return

  _inFlight = true
  // Delay spinner to avoid flicker for fast / cached responses.
  _spinnerTimer = setTimeout(() => {
    _spinnerTimer = null
    if (_inFlight) isGenerating.value = true
  }, SPINNER_DELAY_MS)
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
    clearSlow()
  } else if (result === 'completed') {
    claimSlow(buttonId)
  }
  // NORMAL + interrupted: stay normal.
}

const { onPointerDown: _lpPointerDown, onPointerUp, onCancel: cancelPress } = useLongPress(
  openPopup,
  { onShortPress: () => void _play(), popupRef },
)

function onPointerDown(e: PointerEvent) {
  _longPressPointerId = e.pointerId
  _lpPointerDown(e)
}

/** Opens the voice-picker popup, placed below/left the button with viewport-edge flipping.
 *  Two-pass positioning: initial guess from button rect, refined after nextTick. */
function openPopup() {
  if (!rootRef.value || !props.text) return
  // Clear any text selection the browser may have started during the hold.
  window.getSelection()?.removeAllRanges()
  const rect = rootRef.value.getBoundingClientRect()
  // First-pass guess (good enough until the popup measures itself).
  popupLeft.value = Math.max(8, Math.min(window.innerWidth - 200, rect.left))
  popupTop.value = rect.bottom + 4
  popupVisible.value = true
  emit('longpress')
  // Stop any current playback so the next one is the user's chosen voice.
  stopTts()
  // Click swallowing is handled by useLongPress (popupRef guard).
  _registerLongPressPointerUpGuard()  // prevent focusing a different card on release
  void nextTick(() => { positionPopup(rect); scrollToSelectedVoice() })  // second-pass: refine position once rendered
}

function scrollToSelectedVoice() {
  const scroll = popupScrollRef.value
  if (!scroll) return
  const selected = scroll.querySelector<HTMLElement>('[data-selected]')
  if (!selected) return
  scroll.scrollTop = selected.offsetTop - scroll.clientHeight / 2 + selected.offsetHeight / 2
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

function closePopup() { popupVisible.value = false }
watch(popupVisible, (open) => {
  if (open) {
    document.addEventListener('pointerdown', onOutsidePointerDown, true)
    document.addEventListener('dragstart', onDocumentDragStart, true)
  } else {
    document.removeEventListener('pointerdown', onOutsidePointerDown, true)
    document.removeEventListener('dragstart', onDocumentDragStart, true)
  }
})

function onOutsidePointerDown(e: PointerEvent) {
  // Bail out if the click originated inside the popup (let the item's handler run).
  if (popupRef.value && popupRef.value.contains(e.target as Node)) return
  closePopup()
  // Don't fire a normal click after long-press dismissal.
  e.stopPropagation()
}

/** Close the voice popup when any HTML5 card drag starts. */
function onDocumentDragStart() { closePopup() }

function onChoosePopup(providerCode: string, voiceId: string) {
  closePopup()
  // Record the picked voice as the browser-local default for this lang.
  settings.setDefaultTtsForLang(props.lang, providerCode, voiceId)
  // Popup picks always play at normal speed.
  void _play({ provider: providerCode, voice: voiceId, forceSpeed: 'NORMAL' })
}

// KeepAlive deactivation: teleported popup stays in <body>, close it manually.
onDeactivated(() => {
  _cleanLongPressPointerUpGuard()
  closePopup()
  // pressTimer and click guard are handled by useLongPress
})

onBeforeUnmount(() => {
  _cancelSpinnerTimer()
  _cleanLongPressPointerUpGuard()
  document.removeEventListener('pointerdown', onOutsidePointerDown, true)
  document.removeEventListener('dragstart', onDocumentDragStart, true)
  if (isPlaying.value || _inFlight) stopTts()
  if (isSlowOwner(buttonId)) clearSlow()
  // pressTimer and click guard are handled by useLongPress
})
</script>
