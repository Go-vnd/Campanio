from django.urls import path
from . import views

urlpatterns = [
    # Volunteer URLs
    path("volunteer/dashboard/", views.volunteer_dashboard, name="volunteer_dashboard"),
    path("volunteer/accept/<int:request_id>/", views.accept_request, name="accept_request"),
    path("volunteer/complete/<int:request_id>/", views.complete_request, name="complete_request"),
]

