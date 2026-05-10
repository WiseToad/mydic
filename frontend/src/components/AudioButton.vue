<template>
  <div v-if="!settings.loaded || choices.length > 0" class="relative inline-flex" ref="rootRef">
    <button
      :title="buttonTitle"
      :disabled="!text"
      :class="[
        'inline-flex items-center justify-center rounded-full transition-colors disabled:opacity-30 disabled:cursor-not-allowed',
        size === 'sm' ? 'w-6 h-6' : 'w-8 h-8',
        isPlaying
          ? 'text-primary-400 hover:text-red-400 hover:bg-red-500/10'
          : isSlow
            ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/10'
            : 'text-gray-500 hover:text-primary-400 hover:bg-primary-500/10'
      ]"
      @click.stop="onClick"
      @pointerdown.stop="onPointerDown"
      @pointerup.stop="onPointerUp"
      @pointerleave="onPointerUp"
      @pointercancel="onPointerUp"
      @contextmenu.prevent
    >
      <!-- Stop icon when playing -->
      <svg v-if="isPlaying" xmlns="http://www.w3.org/2000/svg" :class="size === 'sm' ? 'w-4 h-4' : 'w-5 h-5'" viewBox="0 0 24 24" fill="currentColor">
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
        :style="{ left: popupLeft + 'px', top: popupTop + 'px' }"
        class="fixed z-50 max-h-72 overflow-auto bg-surface-900 border border-surface-700 rounded-lg shadow-2xl py-1 min-w-[180px]"
        @pointerdown.stop
        @click.stop
      >
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
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
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

const popupVisible = ref(false)
const popupLeft = ref(0)
const popupTop = ref(0)

let pressTimer: ReturnType<typeof setTimeout> | null = null
let longPressFired = false

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
  if (isPlaying.value) {
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

  isPlaying.value = true
  let result: PlaybackResult
  try {
    result = await playTts(props.text, props.lang, { speed, provider: resolvedProvider, voice: resolvedVoice })
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Could not play audio'))
    return
  } finally {
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
  const rect = rootRef.value.getBoundingClientRect()
  // First-pass guess (good enough until the popup measures itself).
  popupLeft.value = Math.max(8, Math.min(window.innerWidth - 200, rect.left))
  popupTop.value = rect.bottom + 4
  popupVisible.value = true
  // Stop any current playback so the next one is the user's chosen voice.
  stopTts()
  document.addEventListener('pointerdown', onOutsidePointerDown, true)
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
  // Don't fire a normal click after long-press dismissal.
  e.stopPropagation()
}

function onChoosePopup(providerCode: string, voiceId: string) {
  popupVisible.value = false
  document.removeEventListener('pointerdown', onOutsidePointerDown, true)
  // Picking a voice from the popup also records it as the default for this
  // button's language (browser-local), so future plain clicks default to
  // the same voice without altering the user's settings-defined order.
  settings.setDefaultTtsForLang(props.lang, providerCode, voiceId)
  // #9: popup picks unconditionally start a NORMAL-speed playback, even if
  // this button currently owns slow mode.
  void _play({ provider: providerCode, voice: voiceId, forceSpeed: 'NORMAL' })
}

onBeforeUnmount(() => {
  if (pressTimer) clearTimeout(pressTimer)
  document.removeEventListener('pointerdown', onOutsidePointerDown, true)
  // #4: a button being unmounted (e.g. wordbook card filtered out) must
  // stop any playback it initiated and release any slow ownership it held.
  if (isPlaying.value) stopTts()
  if (isSlowOwner(buttonId)) clearSlow()
})
</script>
