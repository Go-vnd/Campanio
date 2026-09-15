from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from .admin_views import (
    admin_dashboard, admin_users, admin_users_export, admin_user_toggle,
    admin_volunteers, admin_volunteer_toggle_verify, admin_issue_certificate, admin_award_volunteer_badge,
    admin_requests, admin_request_assign, admin_analytics, admin_badges, admin_contact_messages
)
from .public_views import index, about, services, contact

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", admin_dashboard, name="admin_dashboard"),
    path("admin/users/", admin_users, name="admin_users"),
    path("admin/users/export/", admin_users_export, name="admin_users_export"),
    path("admin/users/toggle/<int:user_id>/", admin_user_toggle, name="admin_user_toggle"),
    path("admin/volunteers/", admin_volunteers, name="admin_volunteers"),
    path("admin/volunteers/verify/<int:user_id>/", admin_volunteer_toggle_verify, name="admin_volunteer_toggle_verify"),
    path("admin/volunteers/certificate/<int:user_id>/", admin_issue_certificate, name="admin_issue_certificate"),
    path("admin/volunteers/award/<int:user_id>/", admin_award_volunteer_badge, name="admin_award_volunteer_badge"),
    path("admin/requests/", admin_requests, name="admin_requests"),
    path("admin/requests/assign/<int:request_id>/", admin_request_assign, name="admin_request_assign"),
    path("admin/analytics/", admin_analytics, name="admin_analytics"),
    path("admin/badges/", admin_badges, name="admin_badges"),
    path("admin/messages/", admin_contact_messages, name="admin_contact_messages"),
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

