"""Multi-tenant SaaS profile (PLT-1). Tenant resolved from subdomain."""

from config.settings.base import *  # noqa: F401,F403

DEPLOYMENT_PROFILE = "saas"

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
