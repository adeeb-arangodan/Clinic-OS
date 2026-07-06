"""Single-tenant on-prem profile (PLT-3): same schema, exactly one tenant row.

No SaaS-only code paths in domain logic — only deployment concerns differ here.
"""

from config.settings.base import *  # noqa: F401,F403

DEPLOYMENT_PROFILE = "onprem"

SECURE_SSL_REDIRECT = False
