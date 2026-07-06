// Access token lives in memory only (never storage — XSS hygiene); the
// httpOnly refresh cookie restores the session after a page reload.
let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}
