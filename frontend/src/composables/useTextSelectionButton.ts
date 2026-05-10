import { ref, onMounted, onUnmounted, type Ref } from 'vue'

/** Delay (ms) between pointer-up / touch-end and button appearance. */
const SHOW_DELAY = 300

/**
 * Detects text selection within `containerRef` and exposes reactive state
 * for positioning a floating action button underneath the selection.
 * The button appears only after the user finishes selecting (mouseup / touchend)
 * with a short delay, and is left-aligned to the selection's left edge.
 *
 * Usage:
 *   const containerRef = ref<HTMLElement | null>(null)
 *   const { selectedText, buttonVisible, buttonLeft, buttonTop, dismiss } =
 *     useTextSelectionButton(containerRef)
 */
export function useTextSelectionButton(containerRef: Ref<HTMLElement | null>) {
  const selectedText = ref('')
  const buttonVisible = ref(false)
  const buttonLeft = ref(0)
  const buttonTop = ref(0)

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
    // Use the minimum left across all selection rects so the button aligns
    // with the leftmost edge of the highlighted selection background.
    const rects = Array.from(range.getClientRects())
    buttonLeft.value = rects.length ? Math.min(...rects.map(r => r.left)) : rect.left
    buttonTop.value = rect.bottom + 4
    selectedText.value = text
    buttonVisible.value = true
  }

  /** Triggered on mouseup / touchend — starts the delay timer. */
  function onPointerUp() {
    clearTimer()
    showTimer = setTimeout(tryShow, SHOW_DELAY)
  }

  /** Hide and cancel the timer whenever the selection collapses or clears. */
  function onSelectionChange() {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      clearTimer()
      buttonVisible.value = false
      selectedText.value = ''
    }
  }

  onMounted(() => {
    document.addEventListener('selectionchange', onSelectionChange)
    document.addEventListener('mouseup', onPointerUp)
    document.addEventListener('touchend', onPointerUp)
    window.addEventListener('scroll', dismiss, { passive: true })
    window.addEventListener('resize', dismiss)
  })

  onUnmounted(() => {
    clearTimer()
    document.removeEventListener('selectionchange', onSelectionChange)
    document.removeEventListener('mouseup', onPointerUp)
    document.removeEventListener('touchend', onPointerUp)
    window.removeEventListener('scroll', dismiss)
    window.removeEventListener('resize', dismiss)
  })

  function dismiss() {
    clearTimer()
    buttonVisible.value = false
    selectedText.value = ''
    window.getSelection()?.removeAllRanges()
  }

  return { selectedText, buttonVisible, buttonLeft, buttonTop, dismiss }
}
