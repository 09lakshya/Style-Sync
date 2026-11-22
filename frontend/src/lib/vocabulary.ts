/** The one vocabulary for occasions and seasons, shared by the add, edit and
 *  filter forms. The values are what the backend stores and the outfit builder
 *  ranks by (CANDIDATE_OCCASIONS / CANDIDATE_SEASONS); the labels are only for
 *  display. Keep both lists in step with backend/app/modules/ai/service.py. */

// Garment types, grouped for the add and edit forms.
// Mirrors TYPE_PROMPTS in the backend's ai service. Grouped so the traditional
// wear is findable rather than buried among the western names.
export const GARMENT_GROUPS: { label: string; types: string[] }[] = [
  {
    label: 'Western',
    types: [
      'dress', 'gown', 'shirt', 'blouse', 'top', 't-shirt', 'skirt', 'pants',
      'jeans', 'shorts', 'jumpsuit', 'romper', 'jacket', 'coat', 'blazer',
      'sweater', 'hoodie', 'cardigan', 'waistcoat',
    ],
  },
  {
    label: 'Indian traditional',
    types: [
      'saree', 'lehenga', 'choli', 'anarkali', 'salwar kameez', 'patiala salwar',
      'churidar', 'palazzo', 'sharara', 'gharara', 'kurta', 'kurti', 'angrakha',
      'sherwani', 'bandhgala', 'nehru jacket', 'pathani suit', 'dhoti', 'lungi',
      'mekhela chador', 'pattu pavadai', 'phiran', 'indo-western gown', 'dupatta',
    ],
  },
]

export interface VocabularyOption {
  value: string
  label: string
}

export const OCCASIONS: readonly VocabularyOption[] = [
  { value: 'casual', label: 'Casual' },
  { value: 'day_out', label: 'Day out' },
  { value: 'work', label: 'Office' },
  { value: 'evening', label: 'Evening' },
  { value: 'party', label: 'Party' },
  { value: 'festive', label: 'Festive' },
  { value: 'formal', label: 'Formal' },
  { value: 'wedding', label: 'Wedding' },
  { value: 'sports', label: 'Sports' },
]

export const SEASONS: readonly VocabularyOption[] = [
  { value: 'spring', label: 'Spring' },
  { value: 'summer', label: 'Summer' },
  { value: 'fall', label: 'Fall' },
  { value: 'winter', label: 'Winter' },
  { value: 'all_season', label: 'All season' },
]

/** Older words for an occasion, mapped the same way the backend maps them. */
const OCCASION_SYNONYMS: Record<string, string> = {
  office: 'work',
  college: 'casual',
  everyday: 'casual',
  travel: 'day_out',
  sport: 'sports',
  gym: 'sports',
  festival: 'festive',
  traditional: 'festive',
}

/** Canonical occasion value for anything the API or an old item might hold. */
export function toOccasion(value: string | null | undefined): string | null {
  const cleaned = (value ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_')
  if (!cleaned) return null
  const mapped = OCCASION_SYNONYMS[cleaned] ?? cleaned
  return OCCASIONS.some((option) => option.value === mapped) ? mapped : null
}

export function occasionLabel(value: string): string {
  const canonical = toOccasion(value) ?? value
  return OCCASIONS.find((option) => option.value === canonical)?.label ?? value.replace(/_/g, ' ')
}

export function seasonLabel(value: string): string {
  const canonical = value.trim().toLowerCase().replace(/[\s-]+/g, '_')
  return SEASONS.find((option) => option.value === canonical)?.label ?? value.replace(/_/g, ' ')
}
