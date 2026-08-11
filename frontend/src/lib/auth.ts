import type { AuthSession } from '../features/auth/authTypes'

const SESSION_KEY = 'stylesync-session'

export function readStoredSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as AuthSession
    if (parsed && parsed.user && typeof parsed.token === 'string') {
      return parsed
    }
    return null
  } catch {
    return null
  }
}

export function saveStoredSession(session: AuthSession): void {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  } catch (error) {
    console.error('Failed to save authentication session:', error)
  }
}

export function removeStoredSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY)
  } catch (error) {
    console.error('Failed to remove authentication session:', error)
  }
}

export function getAuthHeader(token?: string): Record<string, string> {
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}
