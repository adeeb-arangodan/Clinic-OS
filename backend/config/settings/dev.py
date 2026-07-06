from config.settings.base import *  # noqa: F401,F403

DEBUG = True

SECRET_KEY = SECRET_KEY or "dev-only-insecure-key-0123456789-0123456789"  # noqa: F405 — ≥32B for HS256

ALLOWED_HOSTS = ALLOWED_HOSTS or ["*"]  # noqa: F405

JWT_COOKIE_SECURE = False  # no TLS on localhost
