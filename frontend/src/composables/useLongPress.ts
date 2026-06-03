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
    /**
     * When true, a one-shot capture-phase `click` guard is registered after the
     * long-press fires, suppressing the browser's synthetic post-release click on
     * the trigger element.  Use this when there is no popup element to anchor the
     * guard to but the spurious click on the trigger still needs suppression (e.g.
     * a long-press that triggers an action elsewhere rather than opening a popup on
     * this element).  Unlike `popupRef`, this only swallows clicks that land on or
     * within the trigger element itself — clicks on any other element (e.g. a popup
     * opened by the long-press action) pass through unaffected.
     * Ignored when `popupRef` is also provided — `popupRef` already enables the guard.
     */
    suppressClickAfterLongPress?: boolean
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
  const { onShortPress, popupRef, suppressClickAfterLongPress } = options ?? {}

  let timer: ReturnType<typeof setTimeout> | null = null
  let clickGuard: ((e: MouseEvent) => void) | null = null
  let _triggerEl: HTMLElement | null = null
  let _capturedPointerId: number | null = null

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
    const triggerEl = _triggerEl
    const handler = (e: MouseEvent) => {
      document.removeEventListener('click', handler, true)
      clickGuard = null
      if (popupRef?.value?.contains(e.target as Node)) return
      // When suppressClickAfterLongPress is used without a popupRef, only suppress
      // clicks that land on or within the trigger element (the spurious synthetic
      // click from the long-press gesture).  Clicks on other elements — such as a
      // popup opened by the long-press action — pass through unaffected.
      if (!popupRef && triggerEl && !triggerEl.contains(e.target as Node)) return
      e.stopPropagation()
      e.preventDefault()
    }
    clickGuard = handler
    document.addEventListener('click', handler, true)
  }

  function onPointerDown(e: PointerEvent) {
    if (e.button !== 0) return
    _triggerEl = e.currentTarget as HTMLElement | null
    _capturedPointerId = e.pointerId
    // Explicit pointer capture ensures pointerup/pointercancel are always
    // received even when the touch drifts outside the element boundary.
    _triggerEl?.setPointerCapture(e.pointerId)
    _clearTimer()
    timer = setTimeout(() => {
      timer = null
      if (popupRef || suppressClickAfterLongPress) _registerClickGuard()
      onLongPress()
    }, threshold)
  }

  function onPointerUp() {
    _capturedPointerId = null
    if (timer !== null) {
      _clearTimer()
      onShortPress?.()
    }
  }

  function onCancel() {
    // The Pointer Events spec fires pointerleave based on the pointer's
    // *position*, even when explicit capture is active — so pointerleave
    // fires whenever the touch/cursor drifts outside the element's boundary.
    // While capture is still held the pointer is logically still "ours", so
    // we ignore the cancel signal and let the timer run to completion.
    // pointercancel releases capture before the event is dispatched, so
    // hasPointerCapture() returns false for that case and we do cancel.
    if (_capturedPointerId !== null && _triggerEl?.hasPointerCapture(_capturedPointerId)) {
      return
    }
    _clearTimer()
  }

  onBeforeUnmount(() => { _clearTimer(); _cleanClickGuard() })
  onDeactivated(() => { _clearTimer(); _cleanClickGuard() })

  return { onPointerDown, onPointerUp, onCancel }
}
