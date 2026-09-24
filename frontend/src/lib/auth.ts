import type { AuthSession } from '../features/auth/authTypes'

const SESSION_KEY = 'stylesync-session'

/** Seconds until a token expires, or null if it carries no readable expiry.
 *
 *  This reads the JWT payload without verifying the signature, which is the
 *  right trade here: the client cannot verify anything the server has not
 *  already signed, and it only needs to know whether a token is worth sending.
 *  The server remains the only thing that decides whether a token is valid.
 */
function secondsUntilExpiry(token: string): number | null {
  try {
    const [, encodedPayload] = token.split('.')
    if (!encodedPayload) return null
    const json = atob(encodedPayload.replace(/-/g, '+').replace(/_/g, '/'))
    const { exp } = JSON.parse(json) as { exp?: number }
    if (typeof exp !== 'number') return null
    return exp - Math.floor(Date.now() / 1000)
  } catch {
    return null
  }
}

export function isTokenExpired(token: string): boolean {
  const remaining = secondsUntilExpiry(token)
  // A token with no readable expiry is left alone rather than assumed dead --
  // the server will reject it if it is, and guessing would sign people out of
  // a perfectly good session.
  if (remaining === null) return false
  return remaining <= 0
}

export function readStoredSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as AuthSession
    if (!parsed || !parsed.user || typeof parsed.token !== 'string') {
      return null
    }
    // Tokens last 24 hours. Without this check a day-old session still looked
    // valid here, so the app rendered the dashboard as if signed in and every
    // request behind it answered 401 -- an app that looks logged in but cannot
    // load anything, with no way back to the login screen.
    if (isTokenExpired(parsed.token)) {
      removeStoredSession()
      return null
    }
    return parsed
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
