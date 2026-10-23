from django.urls import path
from . import views

app_name = 'assist_requests'

urlpatterns = [
    path('', views.request_list, name='request_list'),
    path('create/', views.request_create, name='request_create'),
    path('<int:pk>/', views.request_detail, name='request_detail'),
    path('<int:pk>/accept/', views.request_accept, name='request_accept'),
    path('<int:pk>/complete/', views.request_complete, name='request_complete'),
    path('<int:pk>/cancel/', views.request_cancel, name='request_cancel'),
]
