/** Response of POST /recommendations/analyze-outfit. */
export interface OutfitPiece {
  slot: string
  name: string
  color: string
  pattern?: string
  details?: string
}

export interface ColorChip {
  name: string
  hex: string
}

export interface ColorPaletteInfo {
  primary_color: string
  secondary_colors: string[]
  color_chips?: ColorChip[]
  harmony_type?: string
  harmony_evaluation?: string
}

export interface StylistCritique {
  strengths?: string[]
  elevation_tips?: string[]
}

export interface OutfitAnalysis {
  engine?: 'gemini_multimodal_vision' | 'local_vision_models'
  outfit_score?: number
  aesthetic?: string
  summary?: string
  detected_pieces?: OutfitPiece[]
  color_palette?: ColorPaletteInfo
  silhouette_and_proportions?: {
    fit?: string
    evaluation?: string
  }
  stylist_critique?: StylistCritique
  styling_recommendations?: {
    footwear?: string[]
    bag?: string[]
    jewellery_and_watches?: string[]
    layers_and_outerwear?: string[]
    other_accessories?: string[]
  }
  classification: {
    available: boolean
    predicted_category: string | null
    /** Every label to show, the one driving the styling first, e.g. ['Ethnic', 'Formal']. */
    labels: string[]
    prediction_confidence: number | null
    model_version: string | null
  }
  attributes: {
    available: boolean
    reason: string | null
    type: string | null
    primary_color: string
    secondary_colors: string[]
    pattern: string
    sleeve_type: string | null
    season: string[]
    occasion: string[]
    confidence: Record<string, number>
  }
  gender?: {
    value: OutfitGender
    source: 'detected' | 'provided' | 'profile' | 'unavailable'
    confidence: number | null
  }
  tags: string[]
  styling: {
    available: boolean
    reason?: string
    style?: string
    metal_tone?: string
    reasoning?: string[]
    slots: Record<string, string[]>
  }
  source_note: string
}

export type OutfitGender = 'female' | 'male' | 'unisex'

/** Order the accessory slots are presented in. */
export const STYLING_SLOTS = [
  'footwear',
  'bag',
  'earrings',
  'necklace',
  'bracelet',
  'watch',
  'other',
] as const
