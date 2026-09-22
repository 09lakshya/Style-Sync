import type { ProfileGender } from '../features/auth/authTypes'
import type { WardrobeItem } from '../types/wardrobe'

/**
 * Copy and suggestions that change with who the user is and what they own.
 *
 * Two inputs, deliberately separate:
 *   - profile gender decides which garment vocabulary to speak in. A wardrobe
 *     app that suggests "add a saree" to someone who wears sherwanis is worse
 *     than one that says nothing.
 *   - the wardrobe itself decides what is worth saying right now. An empty
 *     wardrobe needs a different line from a well-worn one.
 *
 * Nothing here assigns a colour. The palette comes from `lib/theme.ts`, which
 * reads the user's own clothes.
 */

export interface PersonalCopy {
  /** Short label for the signed-in header. */
  profileLabel: string
  heroEyebrow: string
  heroBody: string
  wardrobeSubtitle: string
  emptyWardrobe: string
  /** Garment types worth suggesting to this profile. */
  suggestedGarments: string[]
}

const GARMENTS: Record<ProfileGender, string[]> = {
  female: ['Kurti', 'Saree', 'Lehenga', 'Anarkali', 'Dress', 'Blouse', 'Skirt', 'Trousers'],
  male: ['Kurta', 'Sherwani', 'Nehru jacket', 'Bandhgala', 'Shirt', 'Blazer', 'Trousers', 'Jeans'],
  'non-binary': ['Kurta', 'Kurti', 'Shirt', 'Blazer', 'Trousers', 'Dress', 'Jacket', 'Jeans'],
  unspecified: ['Kurta', 'Kurti', 'Shirt', 'Blazer', 'Trousers', 'Dress', 'Jacket', 'Jeans'],
}

const PROFILE_LABELS: Record<ProfileGender, string> = {
  female: 'Womenswear',
  male: 'Menswear',
  'non-binary': 'All styling',
  unspecified: 'All styling',
}

const EYEBROWS: Record<ProfileGender, string> = {
  female: 'Womenswear · Digital wardrobe',
  male: 'Menswear · Digital wardrobe',
  'non-binary': 'Digital wardrobe',
  unspecified: 'Digital wardrobe',
}

export function resolveGender(gender: string | undefined): ProfileGender {
  if (gender === 'female' || gender === 'male' || gender === 'non-binary') return gender
  return 'unspecified'
}

export function personalCopy(
  gender: string | undefined,
  items: WardrobeItem[],
  accentSource: string,
): PersonalCopy {
  const profile = resolveGender(gender)
  const count = items.length
  const worn = items.filter((item) => item.wearCount > 0).length
  const hasPalette = accentSource !== 'default'

  // The hero says what is true of this wardrobe right now, not a fixed pitch.
  let heroBody: string
  if (count === 0) {
    heroBody =
      'Add your first piece and StyleSync reads its type, colour, pattern and fabric from the photo — including traditional wear — then scores this season’s trends against what you own.'
  } else if (worn === 0) {
    heroBody = `${count} piece${count === 1 ? '' : 's'} catalogued, none worn yet. Mark what you wear and your trends, reminders and palette start following your real rotation.`
  } else if (hasPalette) {
    heroBody = `${count} pieces, ${worn} in rotation. Your wardrobe reads ${accentSource} — the app is tinted to match, and your trends are scored against these clothes.`
  } else {
    heroBody = `${count} pieces, ${worn} in rotation. Trends below are scored against what you actually own, not a generic list.`
  }

  const wardrobeSubtitle =
    count === 0
      ? 'Nothing here yet — add a photo and the details fill themselves in.'
      : `Browse, search and manage your ${count} catalogued piece${count === 1 ? '' : 's'}.`

  return {
    profileLabel: PROFILE_LABELS[profile],
    heroEyebrow: EYEBROWS[profile],
    heroBody,
    wardrobeSubtitle,
    emptyWardrobe:
      profile === 'male'
        ? 'Start with what you reach for most — a kurta, a shirt, a blazer.'
        : profile === 'female'
          ? 'Start with what you reach for most — a kurti, a saree, a dress.'
          : 'Start with what you reach for most — a kurta, a shirt, a dress.',
    suggestedGarments: GARMENTS[profile],
  }
}
