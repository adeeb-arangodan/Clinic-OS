// Tenant resolution mirrors the backend TenantMiddleware (docs/03 §3):
// {tenant}.sehaerp.sa in production; the X-Tenant header carries it always,
// with VITE_TENANT as the dev/on-prem fallback (single value on-prem, PLT-3).
export function tenantSubdomain(): string {
  const labels = window.location.hostname.split('.')
  if (labels.length >= 3) return labels[0]
  return import.meta.env.VITE_TENANT ?? 'demo'
}
