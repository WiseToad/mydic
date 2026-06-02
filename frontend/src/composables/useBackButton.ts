/**
 * System back button handler registry.
 *
 * App.vue pushes a sentinel browser history entry on mount and listens for
 * popstate (triggered by the Android back key, the browser back button, etc.).
 * On each event the sentinel is re-pushed so the app is never actually
 * navigated away from, and dispatchBackButton() is called to run the handlers.
 *
 * Components register a handler via registerBackHandler() and receive a
 * cleanup function to unregister it.  Handlers are called in LIFO order
 * (last registered = first called) until one returns true.
 */

type BackHandler = () => boolean

const _handlers: BackHandler[] = []

/** Register a back-press handler.  Returns a function that unregisters it. */
export function registerBackHandler(handler: BackHandler): () => void {
  _handlers.push(handler)
  return () => {
    const i = _handlers.lastIndexOf(handler)
    if (i !== -1) _handlers.splice(i, 1)
  }
}

/**
 * Run handlers in reverse registration order until one returns true.
 * Returns true if any handler consumed the event.
 */
export function dispatchBackButton(): boolean {
  for (let i = _handlers.length - 1; i >= 0; i--) {
    if (_handlers[i]()) return true
  }
  return false
}
