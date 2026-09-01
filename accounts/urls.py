from django.contrib.auth import views as auth_views
from django.urls import path
from .views import (
    register, dashboard, profile, 
    user_dashboard, create_request, request_history,
    feedback, user_chat, user_notifications
)

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
    path("profile/", profile, name="user_profile"),
    path("user-dashboard/", user_dashboard, name="user_dashboard"),
    path("create-request/", create_request, name="create_request"),
    path("request-history/", request_history, name="request_history"),
    path("feedback/<int:request_id>/", feedback, name="feedback"),
    path("chat/", user_chat, name="user_chat"),
    path("notifications/", user_notifications, name="user_notifications"),
]
