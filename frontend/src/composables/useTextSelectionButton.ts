import { ref, onMounted, onUnmounted, type Ref } from 'vue'

/** Delay (ms) between pointer-up / touch-end and button appearance. */
const SHOW_DELAY = 300

/**
 * Detects text selection within `containerRef` and exposes reactive state
 * for positioning a floating action button underneath the selection.
 * The button appears only after the user finishes selecting (mouseup / touchend)
 * with a short delay, and is left-aligned to the selection's left edge for
 * multi-line selections.  For single-line selections the button is horizontally
 * centred over the selection via `buttonTransform = 'translateX(-50%)'` —
 * apply it to the floating button's `transform` style so CSS offsets by exactly
 * half the button's actual rendered width without any hardcoded values.
 *
 * Usage:
 *   const containerRef = ref<HTMLElement | null>(null)
 *   const { selectedText, buttonVisible, buttonLeft, buttonTop, buttonTransform, dismiss } =
 *     useTextSelectionButton(containerRef)
 */
export function useTextSelectionButton(containerRef: Ref<HTMLElement | null>) {
  const selectedText = ref('')
  const buttonVisible = ref(false)
  const buttonLeft = ref(0)
  const buttonTop = ref(0)
  const buttonTransform = ref('')

  let showTimer: ReturnType<typeof setTimeout> | null = null

  function clearTimer() {
    if (showTimer !== null) {
      clearTimeout(showTimer)
      showTimer = null
    }
  }

  /** Called after the delay — reads the current selection and shows the button. */
  function tryShow() {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed || !containerRef.value) return

    const range = selection.getRangeAt(0)
    if (!containerRef.value.contains(range.commonAncestorContainer)) return

    const text = selection.toString().trim()
    if (!text) return

    const rect = range.getBoundingClientRect()
    const rects = Array.from(range.getClientRects())
    // Single-line: all rects share the same top (within 2 px for sub-pixel rendering).
    // Set left to the selection centre and let translateX(-50%) handle the button
    // half-width offset in CSS — no hardcoded pixel values needed.
    // Multi-line: keep the original left-aligned behaviour.
    const tops = rects.map(r => r.top)
    const isSingleLine = tops.length === 0 || Math.max(...tops) - Math.min(...tops) < 2
    if (isSingleLine) {
      const minLeft = rects.length ? Math.min(...rects.map(r => r.left)) : rect.left
      const maxRight = rects.length ? Math.max(...rects.map(r => r.right)) : rect.right
      buttonLeft.value = (minLeft + maxRight) / 2
      buttonTransform.value = 'translateX(-50%)'
    } else {
      buttonLeft.value = rects.length ? Math.min(...rects.map(r => r.left)) : rect.left
      buttonTransform.value = ''
    }
    buttonTop.value = rect.bottom + 4
    selectedText.value = text
    buttonVisible.value = true
  }

  /** Triggered on mouseup (PC) — starts the delay timer. */
  function onPointerUp() {
    clearTimer()
    showTimer = setTimeout(tryShow, SHOW_DELAY)
  }

  /** Hide and cancel the timer whenever the selection collapses or clears.
   * Also debounces the button show when a non-collapsed selection stabilises.
   * Using selectionchange (rather than touchend) avoids false triggers from
   * scroll gestures, which also fire touchend on Android.
   */
  function onSelectionChange() {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      clearTimer()
      buttonVisible.value = false
      selectedText.value = ''
      return
    }
    // Non-collapsed selection changed — debounce the button show.
    // This replaces the touchend path for touch devices: selectionchange fires
    // while the user drags handles and stabilises when they stop, but is never
    // fired by a scroll gesture, preventing false positives.
    const range = selection.getRangeAt(0)
    if (containerRef.value?.contains(range.commonAncestorContainer)) {
      clearTimer()
      showTimer = setTimeout(tryShow, SHOW_DELAY)
    }
  }

  /**
   * Hide the button and cancel the timer, but do NOT clear the selection.
   * Used by scroll and resize handlers so that the Android virtual keyboard
   * is not dismissed: on Android Chrome, calling removeAllRanges() while an
   * input is focused causes the browser to drop focus and close the keyboard.
   * The resize event fires when the keyboard itself opens (viewport shrinks),
   * so we must avoid removeAllRanges() in that path.
   */
  function dismissSilently() {
    clearTimer()
    buttonVisible.value = false
    selectedText.value = ''
  }

  /**
   * Hide the button AND clear the text selection. Only called for explicit
   * user-initiated actions (e.g. clicking the floating translate button)
   * where deselecting the highlighted text is intentional.
   */
  function dismiss() {
    dismissSilently()
    window.getSelection()?.removeAllRanges()
  }

  onMounted(() => {
    document.addEventListener('selectionchange', onSelectionChange)
    document.addEventListener('mouseup', onPointerUp) // PC fast path
    // touchend intentionally omitted: scroll gestures also fire touchend on
    // Android, causing false button shows. Touch selection is handled via the
    // selectionchange debounce in onSelectionChange instead.
    window.addEventListener('scroll', dismissSilently, { passive: true })
    window.addEventListener('resize', dismissSilently)
  })

  onUnmounted(() => {
    clearTimer()
    document.removeEventListener('selectionchange', onSelectionChange)
    document.removeEventListener('mouseup', onPointerUp)
    window.removeEventListener('scroll', dismissSilently)
    window.removeEventListener('resize', dismissSilently)
  })

  return { selectedText, buttonVisible, buttonLeft, buttonTop, buttonTransform, dismiss }
}
