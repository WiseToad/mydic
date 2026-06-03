/**
 * Application back-button history management.
 *
 * Each meaningful interruptible state (dialog, settings view) calls push() to
 * add a real browser history entry paired with a close callback.
 *
 * On back button press (popstate), onPopState() dispatches to the topmost
 * callback.  When a state is dismissed without the back button, popIfTop()
 * removes its entry from both the callback stack and browser history
 * (suppressing the resulting popstate).
 *
 * After any close the browser history length stays bounded: the transient
 * forward entry left by the back/programmatic navigation is naturally
 * truncated the next time push() is called from that position.
 */

type BackCallback = () => void

const _stack: BackCallback[] = []
let _suppressedPops = 0

/** Push a new back-intercept entry.  Adds a real browser history entry. */
export function push(cb: BackCallback): void {
  history.pushState({ _app: true }, '')
  _stack.push(cb)
}

/**
 * Programmatically remove an entry when its owner is dismissed without the
 * back button.  Only acts if cb is still the top of the stack.
 * Returns true if the entry was removed.
 */
export function popIfTop(cb: BackCallback): boolean {
  if (_stack.length === 0 || _stack[_stack.length - 1] !== cb) return false
  _stack.pop()
  _suppressedPops++
  history.back()
  return true
}

/**
 * Handle a popstate event.  Must be called from the app's popstate listener.
 * Returns true if the event was handled or suppressed, false if ignored.
 */
export function onPopState(): boolean {
  if (_suppressedPops > 0) {
    _suppressedPops--
    return true
  }
  const cb = _stack.pop()
  if (cb) {
    cb()
    return true
  }
  return false
}
