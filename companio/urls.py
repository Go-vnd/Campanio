from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from .admin_views import admin_dashboard, admin_users, admin_volunteers, admin_requests, admin_analytics, admin_badges
from .public_views import index, about, services, contact

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", admin_dashboard, name="admin_dashboard"),
    path("admin/users/", admin_users, name="admin_users"),
    path("admin/volunteers/", admin_volunteers, name="admin_volunteers"),
    path("admin/requests/", admin_requests, name="admin_requests"),
    path("admin/analytics/", admin_analytics, name="admin_analytics"),
    path("admin/badges/", admin_badges, name="admin_badges"),
    path("accounts/", include("accounts.urls")),
    path("requests/", include("assistance.urls")),
    path("volunteer/", include("volunteering.urls")),
    path("chat/", include("chat.urls")),
    path("notifications/", include("notifications.urls")),
    path("rewards/", include("rewards.urls")),
    path("", index, name="home"),
    path("about/", about, name="about"),
    path("services/", services, name="services"),
    path("contact/", contact, name="contact"),
]
