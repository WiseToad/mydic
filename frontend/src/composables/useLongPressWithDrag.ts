import { onBeforeUnmount, onDeactivated } from 'vue'
import { LONG_PRESS_MS } from '@/utils/ui'

/** Default pointer movement in px that cancels the long-press and signals drag intent. */
const DEFAULT_DRAG_THRESHOLD = 5

/**
 * Mobile-optimized long-press detector with drag-threshold cancellation.
 *
 * Supports two timing modes:
 *
 * **Action-on-release** (default when `onLongPressConfirmed` is provided):
 *   1. `onTimerFired` fires at the threshold — use for a mid-hold visual "ready" cue
 *      (e.g. switching cursor to `cursor-text` to signal that releasing will commit).
 *   2. `onLongPressConfirmed` fires on `pointerup` after the timer has fired.
 *   3. `onShortPress` fires on `pointerup` before the timer fires.
 *   This lets the user abort by dragging instead of lifting — ideal for rename or
 *   other destructive gestures where a visual warning before commit improves UX.
 *
 * **Action-on-press** (when only `onTimerFired` is provided):
 *   The action fires immediately when the timer fires.  `onShortPress` still fires
 *   for quick taps.  Equivalent to `useLongPress` but with drag-cancellation added.
 *
 * Movement beyond `dragThreshold` (default 5 px) cancels the pending timer and fires
 * `onDragStart(e)` with the current PointerEvent, letting the caller transition into a
 * drag gesture.  In action-on-release mode the drag also suppresses `onLongPressConfirmed`
 * even if the timer had already fired, so the user can abort by dragging mid-hold.
 *
 * The caller is responsible for:
 *  - `touch-action: none` (CSS) on the element — prevents the browser from
 *    treating the touch as a scroll before pointer events are delivered.
 *  - `@contextmenu.prevent` (template) — suppresses the Android native long-press
 *    context menu that would otherwise race with the custom long-press action.
 *
 * @example — action-on-release (group tab rename)
 * const { onPointerDown, onPointerMove, onPointerUp, onPointerCancel } =
 *   useLongPressWithDrag({
 *     onTimerFired:       () => { longPressReadyTabId.value = currentTabId },
 *     onShortPress:       () => selectTab(currentTabId),
 *     onLongPressConfirmed: () => startTabEdit(currentTab),
 *     onDragStart:        (e) => beginTabDrag(e),
 *   })
 *
 * @example — action-on-press (touch card reorder)
 * const { onPointerDown, onPointerMove, onPointerUp, onPointerCancel } =
 *   useLongPressWithDrag({
 *     onTimerFired: () => performCardReorder(focused, target),
 *   })
 */
export function useLongPressWithDrag(options: {
  /**
   * Fires when the long-press timer fires.
   *  - Action-on-release: use for a visual "ready" cue.  Commit the action in
   *    `onLongPressConfirmed` so the user can abort by dragging before releasing.
   *  - Action-on-press: put the action here; omit `onLongPressConfirmed`.
   */
  onTimerFired?: () => void
  /** Fires on `pointerup` when the timer had NOT yet fired (quick tap / short press). */
  onShortPress?: () => void
  /**
   * Fires on `pointerup` when the timer HAD already fired.
   * Enables the action-on-release pattern: the user commits the long-press by lifting
   * their finger, and can abort before that by dragging instead.
   * Omit in action-on-press mode.
   */
  onLongPressConfirmed?: () => void
  /**
   * Fires when pointer movement exceeds `dragThreshold` before the long-press is
   * committed.  The timer is cancelled first (and `onLongPressConfirmed` is suppressed
   * even if the timer had already fired).  Receives the triggering PointerEvent so
   * the caller can initialise a drag ghost at the correct position.
   */
  onDragStart?: (e: PointerEvent) => void
  /** Long-press hold duration in ms. Default: `LONG_PRESS_MS` (500). */
  threshold?: number
  /** Pointer movement in px that cancels the long-press and fires `onDragStart`. Default: 5. */
  dragThreshold?: number
}): {
  /** Attach to `@pointerdown` on the interactive element. */
  onPointerDown: (e: PointerEvent) => void
  /** Attach to `@pointermove` on the element (or a scroll-safe ancestor). */
  onPointerMove: (e: PointerEvent) => void
  /** Attach to `@pointerup` on the element. */
  onPointerUp: (e: PointerEvent) => void
  /** Attach to `@pointercancel` on the element. */
  onPointerCancel: (e: PointerEvent) => void
  /**
   * Programmatically cancel any in-progress long-press (e.g. when a popup
   * containing the element is closed from outside pointer events).
   */
  cancel: () => void
} {
  const threshold = options.threshold ?? LONG_PRESS_MS
  const dragThreshold = options.dragThreshold ?? DEFAULT_DRAG_THRESHOLD
  const { onTimerFired, onShortPress, onLongPressConfirmed, onDragStart } = options

  let timer: ReturnType<typeof setTimeout> | null = null
  /** True once the timer fires (before the gesture ends). */
  let timerFired = false
  /** True once drag threshold is exceeded; suppresses all up-phase callbacks. */
  let dragCancelled = false
  /** True between onPointerDown and the next onPointerUp / onPointerCancel. */
  let active = false
  let startX = 0
  let startY = 0

  function _clearTimer() {
    if (timer !== null) { clearTimeout(timer); timer = null }
  }

  function _reset() {
    _clearTimer()
    timerFired = false
    dragCancelled = false
    active = false
  }

  function onPointerDown(e: PointerEvent) {
    _reset()
    active = true
    startX = e.clientX
    startY = e.clientY
    timer = setTimeout(() => {
      timer = null
      timerFired = true
      onTimerFired?.()
    }, threshold)
  }

  function onPointerMove(e: PointerEvent) {
    if (!active || dragCancelled) return
    const dx = e.clientX - startX
    const dy = e.clientY - startY
    if (Math.abs(dx) > dragThreshold || Math.abs(dy) > dragThreshold) {
      _clearTimer()
      dragCancelled = true
      onDragStart?.(e)
    }
  }

  function onPointerUp(_e: PointerEvent) {
    if (!active) return
    const wasFired = timerFired
    const wasDrag = dragCancelled
    _reset()
    if (wasDrag) return
    if (wasFired) {
      onLongPressConfirmed?.()
    } else {
      onShortPress?.()
    }
  }

  function onPointerCancel(_e: PointerEvent) {
    _reset()
  }

  onBeforeUnmount(_reset)
  onDeactivated(_reset)

  return { onPointerDown, onPointerMove, onPointerUp, onPointerCancel, cancel: _reset }
}
