// Fetch mutator used by every orval-generated call: attaches Authorization +
// X-Tenant, sends cookies (refresh token), converts backend error envelopes
// (docs/03 §3) into typed ApiError, and transparently retries once after a
// silent refresh when an access token expires mid-session.
import { getAccessToken, setAccessToken } from '@/api/auth-token'
import { tenantSubdomain } from '@/api/tenant'

export interface ErrorEnvelope {
  code: string
  message_en: string
  message_ar: string
  field_errors: Record<string, string[]>
}

export class ApiError extends Error {
  readonly status: number
  readonly envelope: ErrorEnvelope

  constructor(status: number, envelope: ErrorEnvelope) {
    super(envelope.message_en)
    this.name = 'ApiError'
    this.status = status
    this.envelope = envelope
  }
}

const FALLBACK_ENVELOPE: ErrorEnvelope = {
  code: 'error.internal',
  message_en: 'Something went wrong. Please try again.',
  message_ar: 'حدث خطأ ما. الرجاء المحاولة مرة أخرى.',
  field_errors: {},
}

function doFetch(url: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers)
  headers.set('X-Tenant', tenantSubdomain())
  const token = getAccessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return fetch(url, { ...init, headers, credentials: 'include' })
}

async function parse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(response.status, body?.code ? body : FALLBACK_ENVELOPE)
  }
  return body as T
}

// Single-flight: concurrent 401s share one refresh round-trip.
let refreshInFlight: Promise<boolean> | null = null

function trySilentRefresh(): Promise<boolean> {
  refreshInFlight ??= doFetch('/api/v1/auth/refresh/', { method: 'POST' })
    .then(async (response) => {
      if (!response.ok) return false
      const body = (await response.json()) as { access: string }
      setAccessToken(body.access)
      return true
    })
    .catch(() => false)
    .finally(() => {
      refreshInFlight = null
    })
  return refreshInFlight
}

export async function customFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await doFetch(url, init)
  // Auth endpoints manage their own 401s (bad password, expired refresh).
  if (response.status === 401 && !url.includes('/auth/') && (await trySilentRefresh())) {
    return parse<T>(await doFetch(url, init))
  }
  return parse<T>(response)
}
