from django.urls import path
from .views import list_notifications, mark_all_read
urlpatterns = [
    path("", list_notifications, name="notifications"),
    path("read-all/", mark_all_read, name="mark_all_read"),
]
