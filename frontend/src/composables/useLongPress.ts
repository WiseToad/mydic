import { onBeforeUnmount, onDeactivated, type Ref } from 'vue'
import { LONG_PRESS_MS } from '@/utils/ui'

/**
 * Manages a single long-press interaction on a button.
 *
 * Handles:
 *  - `setTimeout` / clear-on-release cycle
 *  - Primary-button guard (`e.button !== 0`) so right-clicks are ignored
 *  - `onShortPress` (optional): called on `pointerup` if the hold ended before the threshold
 *  - Post-long-press click guard (when `popupRef` is provided): installs a one-shot
 *    capture-phase `click` listener that swallows the browser's synthetic post-release
 *    click unless it lands inside the popup element
 *  - Timer and guard cleanup on component unmount and KeepAlive deactivation
 *
 * Returns `{ onPointerDown, onPointerUp, onCancel }` — attach them to the
 * corresponding pointer events on the trigger element.
 *
 * @example
 * const { onPointerDown, onPointerUp, onCancel } = useLongPress(openVoicePicker, {
 *   onShortPress: () => void playAudio(),
 *   popupRef: popupRef,
 * })
 */
export function useLongPress(
  onLongPress: () => void,
  options?: {
    /** Hold duration in ms before the long-press action fires. Default: LONG_PRESS_MS. */
    threshold?: number
    /** Called on `pointerup` if the hold ended before the threshold was reached. */
    onShortPress?: () => void
    /**
     * When provided, a one-shot capture-phase `click` guard is registered after the
     * long-press fires.  Clicks inside this element pass through; all others are
     * swallowed, preventing the spurious synthetic click from propagating.
     */
    popupRef?: Ref<HTMLElement | null>
  },
): {
  /** Attach to `@pointerdown`. Starts the long-press timer (primary button only). */
  onPointerDown: (e: PointerEvent) => void
  /** Attach to `@pointerup`. Fires `onShortPress` if the timer was still pending. */
  onPointerUp: () => void
  /** Attach to `@pointerleave` and `@pointercancel`. Cancels the timer silently. */
  onCancel: () => void
} {
  const threshold = options?.threshold ?? LONG_PRESS_MS
  const { onShortPress, popupRef } = options ?? {}

  let timer: ReturnType<typeof setTimeout> | null = null
  let clickGuard: ((e: MouseEvent) => void) | null = null

  function _clearTimer() {
    if (timer !== null) { clearTimeout(timer); timer = null }
  }

  function _cleanClickGuard() {
    if (clickGuard !== null) {
      document.removeEventListener('click', clickGuard, true)
      clickGuard = null
    }
  }

  function _registerClickGuard() {
    _cleanClickGuard()
    const handler = (e: MouseEvent) => {
      document.removeEventListener('click', handler, true)
      clickGuard = null
      if (popupRef?.value?.contains(e.target as Node)) return
      e.stopPropagation()
      e.preventDefault()
    }
    clickGuard = handler
    document.addEventListener('click', handler, true)
  }

  function onPointerDown(e: PointerEvent) {
    if (e.button !== 0) return
    _clearTimer()
    timer = setTimeout(() => {
      timer = null
      if (popupRef) _registerClickGuard()
      onLongPress()
    }, threshold)
  }

  function onPointerUp() {
    if (timer !== null) {
      _clearTimer()
      onShortPress?.()
    }
  }

  function onCancel() {
    _clearTimer()
  }

  onBeforeUnmount(() => { _clearTimer(); _cleanClickGuard() })
  onDeactivated(() => { _clearTimer(); _cleanClickGuard() })

  return { onPointerDown, onPointerUp, onCancel }
}
