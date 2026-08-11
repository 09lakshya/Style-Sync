import type { AuthResponse, AuthSession, LoginPayload, RegisterPayload } from './authTypes'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

async function handleResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Incorrect email or password.')
    }
    if (response.status === 422) {
      if (Array.isArray(payload?.detail) && payload.detail.length > 0) {
        const firstError = payload.detail[0]
        const msg = firstError.msg || 'Invalid input.'
        const field = firstError.loc?.[firstError.loc.length - 1]
        throw new Error(field ? `${field}: ${msg}` : msg)
      }
      throw new Error('Please check your input details.')
    }
    if (response.status >= 500) {
      throw new Error('StyleSync services are temporarily unavailable. Please try again shortly.')
    }
    throw new Error(payload?.detail ?? 'An error occurred during authentication.')
  }

  return payload as T
}

export async function loginApi(payload: LoginPayload): Promise<AuthSession> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: payload.email.trim(),
        password: payload.password,
      }),
    })

    const result = await handleResponse<AuthResponse>(response)
    return {
      user: result.user,
      token: result.access_token,
    }
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Unable to connect to StyleSync backend. Please check your connection.')
    }
    throw error
  }
}

export async function registerApi(payload: RegisterPayload): Promise<AuthSession> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: payload.name.trim(),
        email: payload.email.trim(),
        password: payload.password,
      }),
    })

    const result = await handleResponse<AuthResponse>(response)
    return {
      user: result.user,
      token: result.access_token,
    }
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Unable to connect to StyleSync backend. Please check your connection.')
    }
    throw error
  }
}
