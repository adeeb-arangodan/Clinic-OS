import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter  # noqa: E402

# Websocket routing (queue.{dept}, user.alerts, integration.status) is added
# in M0 deliverable 6 when the first consumer lands.
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
    }
)
