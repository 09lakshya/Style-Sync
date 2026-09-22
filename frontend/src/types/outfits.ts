export type OutfitRole = 'top' | 'bottom' | 'one_piece' | 'layer' | 'accessory'

export interface OutfitPiece {
  role: OutfitRole
  id: string
  name: string
  image_url: string
  type: string
  color: string
  pattern: string
  wear_count: number
}

export interface Outfit {
  id: string
  pieces: OutfitPiece[]
  /** Headline occasion: the dressiest one the outfit covers. */
  occasion: string
  /** Every occasion it genuinely suits, so it can be listed under each. */
  occasions: string[]
  occasion_labels: Record<string, string>
  occasion_label: string
  /** Tradition axis: western, fusion (indo-western) or traditional. */
  style: string
  /** Every style it can be listed under - a kurta with jeans is both
   *  indo-western and, a little, traditional. */
  styles: string[]
  style_labels: Record<string, string>
  seasons: string[]
  score: number
  reasons: string[]
  warnings: string[]
  total_wears: number
}

export interface OutfitSuggestions {
  wardrobe_size: number
  count: number
  gaps: string[]
  outfits: Outfit[]
}

export type OutfitSort = 'score' | 'fresh'

export interface OutfitFilters {
  occasion: string
  season: string
  style: string
  sort: OutfitSort
  groupBy: OutfitGrouping
}

/** Which axis the sections are cut along. */
export type OutfitGrouping = 'occasion' | 'style'

export const OUTFIT_STYLES = ['All', 'western', 'fusion', 'traditional'] as const

export const OUTFIT_OCCASIONS = [
  'All',
  'casual',
  'day_out',
  'work',
  'evening',
  'party',
  'festive',
  'formal',
  'wedding',
  'sports',
] as const

export const OUTFIT_SEASONS = ['All', 'spring', 'summer', 'fall', 'winter'] as const

/** Section order on screen: everyday first, dressiest last. Mirrors
 *  OCCASION_RANK in the backend's outfit rules. */
export const STYLE_ORDER = ['western', 'fusion', 'traditional'] as const

export const OCCASION_ORDER = [
  'casual',
  'day_out',
  'work',
  'evening',
  'party',
  'festive',
  'formal',
  'wedding',
  'sports',
] as const

export const ROLE_LABELS: Record<OutfitRole, string> = {
  top: 'Top',
  bottom: 'Bottom',
  one_piece: 'Whole outfit',
  layer: 'Layer',
  accessory: 'Finish',
}
