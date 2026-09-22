import { getAuthHeader } from '../lib/auth'
import type { OutfitFilters, OutfitSuggestions } from '../types/outfits'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000/api/v1'
).replace(/\/$/, '')

export async function fetchOutfits(
  token: string,
  filters: OutfitFilters,
): Promise<OutfitSuggestions> {
  const params = new URLSearchParams({ sort: filters.sort, limit: '40' })
  if (filters.occasion !== 'All') params.set('occasion', filters.occasion)
  if (filters.season !== 'All') params.set('season', filters.season)
  if (filters.style !== 'All') params.set('style', filters.style)

  const response = await fetch(`${API_BASE_URL}/outfits?${params.toString()}`, {
    headers: getAuthHeader(token),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail ?? `Request failed with status ${response.status}`)
  }
  return payload as OutfitSuggestions
}
