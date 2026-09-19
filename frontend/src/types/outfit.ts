/** Response of POST /recommendations/analyze-outfit.
 *
 * `classification` and `attributes` are model output. `styling` and `tags` are
 * rule-based, derived from those attributes — the UI labels them separately.
 */
export interface OutfitAnalysis {
  classification: {
    available: boolean
    predicted_category: string | null
    prediction_confidence: number | null
    model_version: string | null
  }
  attributes: {
    type: string | null
    primary_color: string
    secondary_colors: string[]
    pattern: string
    sleeve_type: string | null
    season: string[]
    occasion: string[]
    confidence: Record<string, number>
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
  'earrings',
  'necklace',
  'bracelet',
  'watch',
  'footwear',
  'bag',
  'other',
] as const
