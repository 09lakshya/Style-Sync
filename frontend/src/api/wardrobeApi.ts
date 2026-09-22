import { getAuthHeader } from '../lib/auth'
import type {
  ApiWardrobeItem,
  CreateDressInput,
  DetectedDressMetadata,
  UpdateDressMetadataInput,
  WardrobeItem,
} from '../types/wardrobe'

const API_BASE_URL =
  (import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')

export function toWardrobeItem(item: ApiWardrobeItem): WardrobeItem {
  const primaryImg = item.image_url || 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=800&q=80'
  const thumbImg = item.thumbnail_url || item.image_url || primaryImg
  const mediumImg = item.medium_url || item.image_url || primaryImg

  return {
    id: item.id,
    userId: item.user_id,
    name: item.name || 'Untitled Dress',
    imageUrl: primaryImg,
    thumbnailUrl: thumbImg,
    mediumUrl: mediumImg,
    publicId: item.public_id,
    type: item.type || 'dress',
    category: (item.category || 'dresses').replace(/_/g, ' '),
    color: item.color || item.primary_color || 'Unspecified',
    pattern: item.pattern || 'Solid',
    brand: item.brand || '',
    purchaseDate: item.purchase_date ? item.purchase_date.split('T')[0] : '',
    fabric: (item.fabric || 'cotton').replace(/_/g, ' '),
    season: Array.isArray(item.season) ? item.season.map((s) => s.replace(/_/g, ' ')) : ['all season'],
    occasion: Array.isArray(item.occasion)
      ? item.occasion.map((o) => o.replace(/_/g, ' '))
      : ['casual'],
    wearCount: item.wear_count || 0,
    lastWornDate: item.last_worn_date || item.last_worn_at ? (item.last_worn_date || item.last_worn_at)!.split('T')[0] : 'Not worn yet',
    createdAt: item.created_at,
    predictedCategory: item.predicted_category
      ? item.predicted_category.replace(/_/g, ' ')
      : undefined,
    predictionConfidence:
      typeof item.prediction_confidence === 'number' ? item.prediction_confidence : undefined,
    modelVersion: item.model_version || undefined,
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail ?? `Request failed with status ${response.status}`)
  }
  return payload as T
}

export async function detectDressMetadata(
  file: File,
  token: string,
): Promise<DetectedDressMetadata> {
  const formData = new FormData()
  formData.append('image', file)

  const response = await fetch(`${API_BASE_URL}/wardrobe/detect`, {
    method: 'POST',
    headers: getAuthHeader(token),
    body: formData,
  })
  return parseResponse<DetectedDressMetadata>(response)
}

export async function fetchWardrobeItems(token: string): Promise<WardrobeItem[]> {
  const response = await fetch(`${API_BASE_URL}/wardrobe/items`, {
    headers: getAuthHeader(token),
  })
  const payload = await parseResponse<{ items: ApiWardrobeItem[] }>(response)
  return payload.items.map(toWardrobeItem)
}

export async function fetchWardrobeItem(itemId: string, token: string): Promise<WardrobeItem> {
  const response = await fetch(`${API_BASE_URL}/wardrobe/items/${itemId}`, {
    headers: getAuthHeader(token),
  })
  const payload = await parseResponse<{ item: ApiWardrobeItem }>(response)
  return toWardrobeItem(payload.item)
}

export async function createWardrobeItem(
  input: CreateDressInput,
  token: string
): Promise<WardrobeItem> {
  const formData = new FormData()
  if (input.file) {
    formData.append('image', input.file)
  }
  if (input.name.trim()) formData.append('name', input.name.trim())
  if (input.color.trim()) formData.append('color', input.color.trim())
  if (input.pattern.trim()) formData.append('pattern', input.pattern.trim())
  if (input.itemType.trim()) formData.append('item_type', input.itemType.trim())
  if (input.brand.trim()) formData.append('brand', input.brand.trim())
  if (input.purchaseDate) formData.append('purchase_date', input.purchaseDate)
  if (input.occasion.trim()) formData.append('occasion', input.occasion.trim())
  if (input.lastWornDate) formData.append('last_worn_date', input.lastWornDate)

  const response = await fetch(`${API_BASE_URL}/wardrobe/items`, {
    method: 'POST',
    headers: getAuthHeader(token),
    body: formData,
  })
  const payload = await parseResponse<{ item: ApiWardrobeItem }>(response)
  return toWardrobeItem(payload.item)
}

export async function updateWardrobeItem(
  input: UpdateDressMetadataInput,
  token: string
): Promise<WardrobeItem> {
  const response = await fetch(`${API_BASE_URL}/wardrobe/items/${input.id}`, {
    method: 'PUT',
    headers: {
      ...getAuthHeader(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: input.name,
      color: input.color,
      pattern: input.pattern,
      brand: input.brand,
      purchase_date: input.purchaseDate,
      occasion: input.occasion,
      last_worn_date: input.lastWornDate,
      wear_count: input.wearCount,
    }),
  })
  const payload = await parseResponse<{ item: ApiWardrobeItem }>(response)
  return toWardrobeItem(payload.item)
}

/** Records one wearing: adds 1 to the count and sets "last worn" to now, server-side. */
export async function markWardrobeItemWorn(
  itemId: string,
  token: string
): Promise<WardrobeItem> {
  const response = await fetch(`${API_BASE_URL}/wardrobe/items/${itemId}/wear`, {
    method: 'POST',
    headers: getAuthHeader(token),
  })
  const payload = await parseResponse<{ item: ApiWardrobeItem }>(response)
  return toWardrobeItem(payload.item)
}

export async function replaceWardrobeItemImage(
  itemId: string,
  file: File,
  token: string
): Promise<WardrobeItem> {
  const formData = new FormData()
  formData.append('image', file)

  const response = await fetch(`${API_BASE_URL}/wardrobe/items/${itemId}/image`, {
    method: 'PUT',
    headers: getAuthHeader(token),
    body: formData,
  })
  const payload = await parseResponse<{ item: ApiWardrobeItem }>(response)
  return toWardrobeItem(payload.item)
}

export async function deleteWardrobeItem(
  itemId: string,
  token: string
): Promise<{ success: boolean; deleted_item_id: string }> {
  const response = await fetch(`${API_BASE_URL}/wardrobe/items/${itemId}`, {
    method: 'DELETE',
    headers: getAuthHeader(token),
  })
  return parseResponse<{ success: boolean; deleted_item_id: string }>(response)
}
