export type TrendStatus = 'peaking' | 'rising' | 'steady' | 'cooling'

export interface TrendPieceMatch {
  id: string
  name: string
  image_url: string
  primary_color: string
  pattern: string
  wear_count: number
}

export interface TrendKeyPiece {
  label: string
  owned: boolean
  strength: number
  match: TrendPieceMatch | null
  note: string
}

export interface TrendMatch {
  score: number
  owned_count: number
  total_pieces: number
  palette_affinity: number
  verdict: string
  pieces: TrendKeyPiece[]
  missing: string[]
}

export interface Trend {
  id: string
  title: string
  summary: string
  momentum: number
  status: TrendStatus
  season_label: string
  palette: string[]
  patterns: string[]
  seasons: string[]
  occasions: string[]
  styling_tips: string[]
  avoid: string[]
  match: TrendMatch
}

export interface TrendFeed {
  season: string
  updated: string
  wardrobe_size: number
  count: number
  average_match: number
  top_match_id: string | null
  trends: Trend[]
}

export interface TrendSignal {
  id: string
  label: string
  value: string
  detail: string
  direction: 'up' | 'down'
}

export interface TrendSignals {
  wardrobe_size: number
  signals: TrendSignal[]
}

export type TrendSort = 'momentum' | 'match' | 'title'

export interface TrendFilters {
  season: string
  occasion: string
  sort: TrendSort
}

export const TREND_SEASONS = ['All', 'spring', 'summer', 'fall', 'winter'] as const
export const TREND_OCCASIONS = [
  'All',
  'casual',
  'work',
  'formal',
  'party',
  'evening',
  'day_out',
  'sports',
] as const

// Swatch colours for the palette dots; keys match the backend colour vocabulary.
export const COLOR_SWATCHES: Record<string, string> = {
  black: '#1f2328',
  white: '#f6f3ee',
  grey: '#9b9b96',
  beige: '#d9c7a9',
  brown: '#6f4b32',
  navy: '#26344f',
  blue: '#3f6ea8',
  green: '#5d7355',
  red: '#8d2f36',
  pink: '#d39aa4',
  purple: '#5f3f63',
  yellow: '#d8b34a',
  orange: '#c87137',
}
