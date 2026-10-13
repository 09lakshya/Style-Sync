/** Response of POST /recommendations/analyze-outfit.
 *
 * `classification` and `attributes` are model output. `styling` and `tags` are
 * rule-based, derived from those attributes — the UI labels them separately.
 */
export interface OutfitAnalysis {
  classification: {
    available: boolean
    predicted_category: string | null
    /** Every label to show, the one driving the styling first, e.g. ['Ethnic', 'Formal']. */
    labels: string[]
    prediction_confidence: number | null
    model_version: string | null
  }
  /** `available` is false when the attribute model (CLIP) is not loaded; the
   *  fields are then empty rather than placeholder values. */
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
  /** Who the styling targets. Detected by CLIP unless the request overrode it;
   *  'unisex' when the detection was not confident, 'unavailable' when nothing
   *  could be read and no profile answer filled in. */
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
  'earrings',
  'necklace',
  'bracelet',
  'watch',
  'footwear',
  'bag',
  'other',
] as const
