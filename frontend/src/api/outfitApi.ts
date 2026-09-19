import { getAuthHeader } from '../lib/auth'
import type { OutfitAnalysis, OutfitGender } from '../types/outfit'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000/api/v1'
).replace(/\/$/, '')

export async function analyzeOutfit(
  file: File,
  gender: OutfitGender,
  token: string
): Promise<OutfitAnalysis> {
  const formData = new FormData()
  formData.append('image', file)
  formData.append('gender', gender)

  const response = await fetch(`${API_BASE_URL}/recommendations/analyze-outfit`, {
    method: 'POST',
    headers: getAuthHeader(token),
    body: formData,
  })

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail ?? `Analysis failed with status ${response.status}`)
  }
  return payload as OutfitAnalysis
}
