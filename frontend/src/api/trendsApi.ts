import { getAuthHeader } from '../lib/auth'
import type { TrendFeed, TrendFilters, TrendSignals } from '../types/trends'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000/api/v1'
).replace(/\/$/, '')

async function parse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail ?? `Request failed with status ${response.status}`)
  }
  return payload as T
}

export async function fetchTrendFeed(token: string, filters: TrendFilters): Promise<TrendFeed> {
  const params = new URLSearchParams({ sort: filters.sort })
  if (filters.season !== 'All') params.set('season', filters.season)
  if (filters.occasion !== 'All') params.set('occasion', filters.occasion)

  const response = await fetch(`${API_BASE_URL}/trends?${params.toString()}`, {
    headers: getAuthHeader(token),
  })
  return parse<TrendFeed>(response)
}

export async function fetchTrendSignals(token: string): Promise<TrendSignals> {
  const response = await fetch(`${API_BASE_URL}/trends/signals`, {
    headers: getAuthHeader(token),
  })
  return parse<TrendSignals>(response)
}
