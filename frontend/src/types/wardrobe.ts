export interface ApiWardrobeItem {
  id: string
  user_id?: string
  name: string
  image_url: string
  thumbnail_url?: string
  medium_url?: string
  public_id?: string
  type: string
  category: string
  primary_color: string
  color?: string
  secondary_colors?: string[]
  pattern: string
  sleeve_type?: string
  fabric: string
  season: string[]
  occasion: string[]
  brand?: string
  purchase_date?: string
  wear_count: number
  last_worn_at?: string
  last_worn_date?: string
  created_at?: string
  updated_at?: string
  predicted_category?: string
  prediction_confidence?: number
  predicted_axes?: PredictedAxes | null
  model_version?: string
}

/** The classifier's three independent readings of one photo.
 *
 *  occasion and season are genuinely multi-label - a garment can suit both
 *  summer and winter, or name no occasion at all - while tradition is a single
 *  verdict because ethnic and western are complementary. An empty array means
 *  the model cleared no threshold on that axis, which is an answer rather than
 *  missing data.
 *
 *  `probabilities` carries the raw score per label so a recalibration can
 *  re-derive these verdicts without re-running the model over saved photos.
 */
export interface PredictedAxes {
  occasion?: string[]
  season?: string[]
  tradition?: string | null
  probabilities?: Record<string, number>
}

export interface WardrobeItem {
  id: string
  userId?: string
  name: string
  imageUrl: string
  thumbnailUrl: string
  mediumUrl: string
  publicId?: string
  type: string
  category: string
  color: string
  pattern: string
  brand: string
  purchaseDate: string
  fabric: string
  season: string[]
  occasion: string[]
  wearCount: number
  lastWornDate: string
  createdAt?: string
  predictedCategory?: string
  predictionConfidence?: number
  predictedAxes?: PredictedAxes
  modelVersion?: string
}

/** What `POST /wardrobe/detect` returns for a photo, before anything is saved. */
export interface DetectedDressMetadata {
  name: string | null
  type: string | null
  /** Runner-up garment readings, best first, so the form can offer them. */
  type_alternatives: [string, number][]
  category: string | null
  is_ethnic: boolean
  color: string | null
  secondary_colors: string[]
  pattern: string | null
  embellishment: string | null
  sleeve_type: string | null
  fabric: string | null
  season: string[]
  occasion: string[]
  tags: string[]
  confidence: Record<string, number>
  predicted_category: string | null
  prediction_confidence: number | null
  predicted_axes: PredictedAxes | null
  model_version: string | null
}

export interface CreateDressInput {
  file?: File | null
  name: string
  /** Garment type, detected then confirmed or corrected by the user. */
  itemType: string
  color: string
  pattern: string
  brand: string
  purchaseDate: string
  occasion: string
  lastWornDate: string
}

export interface UpdateDressMetadataInput {
  id: string
  name?: string
  color?: string
  pattern?: string
  brand?: string
  purchaseDate?: string
  occasion?: string
  lastWornDate?: string
  wearCount?: number
}

export interface WardrobeFilterState {
  searchQuery: string
  color: string
  pattern: string
  occasion: string
  sortBy: 'recently_added' | 'oldest_added' | 'recently_worn' | 'least_recently_worn'
}
