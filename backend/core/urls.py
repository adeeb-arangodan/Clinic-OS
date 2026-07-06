from django.urls import path

from core import views

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/sessions/", views.SessionListView.as_view(), name="auth-sessions"),
    path(
        "auth/sessions/<uuid:session_id>/revoke/",
        views.SessionRevokeView.as_view(),
        name="auth-session-revoke",
    ),
    path("audit-logs/", views.AuditLogListView.as_view(), name="audit-logs"),
]
