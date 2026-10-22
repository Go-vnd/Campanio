from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('users/', views.manage_users, name='manage_users'),
    path('requests/', views.manage_requests, name='manage_requests'),
    path('reports/', views.manage_reports, name='manage_reports'),
    path('reports/<int:pk>/', views.report_detail, name='report_detail'),
    path('reports/submit/', views.submit_report, name='submit_report'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('reviews/<int:review_id>/toggle-hide/', views.toggle_review_hidden, name='toggle_review_hidden'),
    path('requests/<int:request_id>/messages/', views.request_messages, name='request_messages'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('verification/', views.verification_queue, name='verification_queue'),
    path('verification/<int:user_id>/action/', views.verification_action, name='verification_action'),
    path('users/<int:user_id>/adjust-points/', views.adjust_points, name='adjust_points'),
    path('badges/<int:user_badge_id>/revoke/', views.revoke_badge, name='revoke_badge'),
    path('certificates/<int:cert_id>/revoke/', views.revoke_certificate, name='revoke_certificate'),
    path('badges/', views.manage_badges, name='manage_badges'),
    path('badges/award/', views.award_badge, name='award_badge'),
]




