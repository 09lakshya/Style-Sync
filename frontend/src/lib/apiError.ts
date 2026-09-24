/** An API failure that still knows its HTTP status.
 *
 *  The four api modules each threw `new Error(detail)`, which reads fine in a
 *  toast but loses the one thing a caller needs to tell "your session died"
 *  apart from "that item does not exist". Without the status there is no way to
 *  react to a 401 anywhere except at the call site, and there are seventeen of
 *  those.
 */
export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/** Shared response handling for the api modules. */
export async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(
      payload?.detail ?? `Request failed with status ${response.status}`,
      response.status,
    )
  }
  return payload as T
}
