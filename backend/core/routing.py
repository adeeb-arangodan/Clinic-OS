from django.urls import path

from core.consumers import UserAlertsConsumer

websocket_urlpatterns = [
    path("ws/alerts/", UserAlertsConsumer.as_asgi(), name="ws-alerts"),
]
