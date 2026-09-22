import type { WardrobeItem } from '../types/wardrobe'

/**
 * The accent colour is taken from the wardrobe, not from the profile gender.
 *
 * Two people of the same gender own different clothes, so tying the theme to
 * gender would say less about them than their own rail does. Gender decides
 * which trends and styling conventions apply; this decides what the app looks
 * like. A wardrobe of olive and cream gets an olive app.
 */
export interface AccentTheme {
  /** Colour family the accent was derived from, or 'default' before any items. */
  source: string
  accent: string
  accentHover: string
  /** Tinted background for chips and badges. */
  accentSoft: string
  /** Readable text colour on `accentSoft`. */
  accentInk: string
}

export const DEFAULT_ACCENT: AccentTheme = {
  source: 'default',
  accent: '#a15c38',
  accentHover: '#b56942',
  accentSoft: '#f0e8dd',
  accentInk: '#7f4b2f',
}

// One entry per colour in the backend's CANDIDATE_COLORS. Each is a muted,
// readable version of that family rather than the raw hue, so a wardrobe full
// of bright red does not produce an unusable interface.
const ACCENTS: Record<string, Omit<AccentTheme, 'source'>> = {
  red: { accent: '#9d3b3b', accentHover: '#b04747', accentSoft: '#f3e3e1', accentInk: '#7a2c2c' },
  maroon: { accent: '#7d2f3c', accentHover: '#93394a', accentSoft: '#f1e0e2', accentInk: '#63242f' },
  pink: { accent: '#a4566a', accentHover: '#b96578', accentSoft: '#f5e4e7', accentInk: '#813f51' },
  magenta: { accent: '#8e3d6b', accentHover: '#a4497c', accentSoft: '#f2e2ec', accentInk: '#702f54' },
  purple: { accent: '#6b4a7d', accentHover: '#7d5892', accentSoft: '#ebe4f0', accentInk: '#543a63' },
  blue: { accent: '#3a5f88', accentHover: '#46719f', accentSoft: '#e0e8f1', accentInk: '#2d4a6b' },
  navy: { accent: '#2f4260', accentHover: '#3b5277', accentSoft: '#e1e5ed', accentInk: '#25344b' },
  teal: { accent: '#2f6b6b', accentHover: '#3b8080', accentSoft: '#dfeceb', accentInk: '#255353' },
  green: { accent: '#4a6b46', accentHover: '#597f54', accentSoft: '#e4ece1', accentInk: '#3a5537' },
  olive: { accent: '#5f6438', accentHover: '#727845', accentSoft: '#eaeadb', accentInk: '#4a4e2c' },
  yellow: { accent: '#9a7a24', accentHover: '#b18c2d', accentSoft: '#f4ecd7', accentInk: '#78601d' },
  mustard: { accent: '#8e6f1f', accentHover: '#a58127', accentSoft: '#f2ead3', accentInk: '#6f5718' },
  orange: { accent: '#a1562a', accentHover: '#b96634', accentSoft: '#f4e5da', accentInk: '#7e4321' },
  peach: { accent: '#a4664f', accentHover: '#bb765c', accentSoft: '#f5e6df', accentInk: '#80503e' },
  brown: { accent: '#6f4b32', accentHover: '#85593c', accentSoft: '#ece2d8', accentInk: '#573a27' },
  beige: DEFAULT_ACCENT,
  cream: DEFAULT_ACCENT,
  gold: { accent: '#8a6d2f', accentHover: '#a3813a', accentSoft: '#f2e9d5', accentInk: '#6c5525' },
  silver: { accent: '#5c6066', accentHover: '#6e737a', accentSoft: '#e8e9ea', accentInk: '#484b50' },
  grey: { accent: '#5c6066', accentHover: '#6e737a', accentSoft: '#e8e9ea', accentInk: '#484b50' },
  black: { accent: '#33363a', accentHover: '#44484d', accentSoft: '#e6e6e7', accentInk: '#292b2e' },
  white: DEFAULT_ACCENT,
}

/**
 * Pick the accent from the colours the user actually wears.
 *
 * Wear counts are weighted above ownership: a coat worn thirty times says more
 * about someone than three unworn shirts. Neutrals still win if that is genuinely
 * the wardrobe, which is why white, cream and beige map to the brand default.
 */
export function resolveAccent(items: WardrobeItem[]): AccentTheme {
  if (items.length === 0) return DEFAULT_ACCENT

  const weights = new Map<string, number>()
  for (const item of items) {
    const color = (item.color || '').trim().toLowerCase()
    if (!color || !(color in ACCENTS)) continue
    // One point for owning it, one per wear, so a small worn wardrobe still reads.
    weights.set(color, (weights.get(color) ?? 0) + 1 + item.wearCount)
  }

  let bestColor = ''
  let bestWeight = 0
  for (const [color, weight] of weights) {
    if (weight > bestWeight) {
      bestWeight = weight
      bestColor = color
    }
  }

  if (!bestColor) return DEFAULT_ACCENT
  return { source: bestColor, ...ACCENTS[bestColor] }
}

/** Publish the accent as CSS variables; the components read them via var(). */
export function applyAccent(theme: AccentTheme): void {
  const root = document.documentElement
  root.style.setProperty('--accent', theme.accent)
  root.style.setProperty('--accent-hover', theme.accentHover)
  root.style.setProperty('--accent-soft', theme.accentSoft)
  root.style.setProperty('--accent-ink', theme.accentInk)
}
