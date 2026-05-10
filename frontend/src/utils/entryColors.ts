/**
 * Predefined palette for the optional color tag attached to a wordbook entry.
 *
 * The values are stored verbatim in the backend (`wordbook_entries.color`) but
 * the palette itself lives on the frontend so it can evolve without a database
 * migration.  Backwards-compat note: a stored color that no longer exists in
 * `ENTRY_COLORS` is treated as "no color" by the renderer (see
 * `isEntryColor`), which leaves the original value in place so upgrading the
 * palette later doesn't silently lose data.
 */
export const ENTRY_COLORS = [
  'red',
  'yellow',
  'green',
  'blue',
  'purple',
] as const

export type EntryColor = typeof ENTRY_COLORS[number]

export function isEntryColor(value: unknown): value is EntryColor {
  return typeof value === 'string' && (ENTRY_COLORS as readonly string[]).includes(value)
}

/**
 * Card background classes when a color is set.  Opacities chosen low enough to
 * stay muted on the dark `surface-950` page background — the cards remain
 * readable and the colors aren't vivid.  Listed as full literal strings so the
 * Tailwind JIT picks them up.
 */
export const ENTRY_COLOR_CARD_BG: Record<EntryColor, string> = {
  red: 'bg-red-500/15',
  yellow: 'bg-yellow-500/15',
  green: 'bg-green-500/15',
  blue: 'bg-blue-500/15',
  purple: 'bg-purple-500/15',
}

/** Solid swatch fill used in the picker / filter UI. */
export const ENTRY_COLOR_SWATCH_BG: Record<EntryColor, string> = {
  red: 'bg-red-500/60',
  yellow: 'bg-yellow-500/60',
  green: 'bg-green-500/60',
  blue: 'bg-blue-500/60',
  purple: 'bg-purple-500/60',
}

/** Human-readable labels for the filter popup. */
export const ENTRY_COLOR_LABEL: Record<EntryColor, string> = {
  red: 'Red',
  yellow: 'Yellow',
  green: 'Green',
  blue: 'Blue',
  purple: 'Purple',
}
