from config.settings.base import *  # noqa: F401,F403

SECRET_KEY = "test-only-key-0123456789-0123456789-not-for-production"  # ≥32 bytes for HS256

ALLOWED_HOSTS = ["*"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True

JWT_COOKIE_SECURE = False

CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}
