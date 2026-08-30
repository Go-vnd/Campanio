from django.urls import path
from .views import create_request, request_history, feedback, user_chat, user_notifications, user_profile

urlpatterns = [
    path("create/", create_request, name="create_request"),
    path("history/", request_history, name="request_history"),
    path("<int:request_id>/feedback/", feedback, name="feedback"),
    path("chat/", user_chat, name="user_chat"),
    path("notifications/", user_notifications, name="user_notifications"),
    path("profile/", user_profile, name="user_profile"),
]
