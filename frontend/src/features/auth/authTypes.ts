export type AuthUser = {
  id: string
  name: string
  email: string
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
  general?: string
}
