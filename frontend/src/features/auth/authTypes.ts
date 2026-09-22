/** What the user tells us at sign-up. Drives which trends and styling rules
 *  apply, never a colour on its own. "unspecified" is a real answer. */
export type ProfileGender = 'female' | 'male' | 'non-binary' | 'unspecified'

export type AuthUser = {
  id: string
  name: string
  email: string
  gender?: ProfileGender
}

export type AuthSession = {
  user: AuthUser
  token: string
}

export type LoginPayload = {
  email: string
  password: string
}

export type RegisterPayload = {
  name: string
  email: string
  password: string
  gender: ProfileGender
}

export type AuthResponse = {
  user: AuthUser
  access_token: string
  token_type: string
}

export type FormErrors = {
  name?: string
  email?: string
  password?: string
  gender?: string
  general?: string
}

export const GENDER_OPTIONS: { value: ProfileGender; label: string }[] = [
  { value: 'female', label: 'Woman' },
  { value: 'male', label: 'Man' },
  { value: 'non-binary', label: 'Non-binary' },
  { value: 'unspecified', label: 'Prefer not to say' },
]
