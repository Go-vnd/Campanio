from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    path('<int:request_id>/submit/', views.submit_feedback, name='submit_feedback'),
]
