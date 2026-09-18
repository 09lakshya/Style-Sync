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
  model_version?: string
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
  modelVersion?: string
}

export interface CreateDressInput {
  file?: File | null
  name: string
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
}

export interface WardrobeFilterState {
  searchQuery: string
  color: string
  pattern: string
  occasion: string
  sortBy: 'recently_added' | 'oldest_added' | 'recently_worn' | 'least_recently_worn'
}
