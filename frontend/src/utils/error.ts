/** Extract a human-readable message from an API error or generic Error. */
export function extractErrorMessage(e: unknown, fallback = 'An unexpected error occurred'): string {
  // Axios error with a FastAPI detail payload
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
  if (detail) {
    return typeof detail === 'string' ? detail : JSON.stringify(detail)
  }
  // Standard Error
  const msg = (e as Error)?.message
  return msg || fallback
}
