/** A wardrobe match returned by POST /shopping/check, already ranked by the backend. */
export interface SimilarItem {
  id: string
  name: string
  imageUrl: string
  similarity: number
  reason: string
}

/** Backend duplicate-check verdict. Thresholds live in the backend, not here. */
export type DuplicateDecision = 'similar_found' | 'review_matches' | 'no_strong_duplicate'

export interface DuplicateCheckResult {
  decision: DuplicateDecision
  highestSimilarity: number
  similarItems: SimilarItem[]
}
