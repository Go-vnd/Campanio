from django.urls import path
from . import views

urlpatterns = [
    # Request action endpoints
    path("accept/<int:request_id>/", views.accept_request, name="accept_request"),
    path("complete/<int:request_id>/", views.complete_request, name="complete_request"),
]

