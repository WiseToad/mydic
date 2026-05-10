/** Strip leading/trailing whitespace and collapse internal runs to a single space. */
export function normalizeText(text: string): string {
  return text.trim().replace(/\s+/g, ' ')
}
