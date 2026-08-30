from django.urls import path
from .views import dashboard, accepted_requests, accept_request, skills, availability, rewards, chat, profile

urlpatterns = [
    path("dashboard/", dashboard, name="volunteer_dashboard"),
    path("accepted/", accepted_requests, name="accepted_requests"),
    path("accept/<int:request_id>/", accept_request, name="accept_request"),
    path("skills/", skills, name="volunteer_skills"),
    path("availability/", availability, name="volunteer_availability"),
    path("rewards/", rewards, name="volunteer_rewards"),
    path("chat/", chat, name="volunteer_chat"),
    path("profile/", profile, name="volunteer_profile"),
]
