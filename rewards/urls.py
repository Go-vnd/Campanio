from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('', views.rewards_view, name='rewards'),
    path('certificate/<int:pk>/download/', views.download_certificate, name='download_certificate'),
]
