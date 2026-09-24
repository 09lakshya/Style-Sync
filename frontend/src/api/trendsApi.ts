import { getAuthHeader } from '../lib/auth'
import { parseResponse } from '../lib/apiError'
import type { TrendFeed, TrendFilters, TrendSignals } from '../types/trends'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000/api/v1'
).replace(/\/$/, '')

const parse = parseResponse

export async function fetchTrendFeed(token: string, filters: TrendFilters): Promise<TrendFeed> {
  const params = new URLSearchParams({ sort: filters.sort })
  if (filters.season !== 'All') params.set('season', filters.season)
  if (filters.occasion !== 'All') params.set('occasion', filters.occasion)
  if (filters.allGenders) params.set('all_genders', 'true')

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
