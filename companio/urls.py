"""
URL configuration for companio project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, redirect
from accounts.models import CustomUser
from assist_requests.models import Request


def home_view(request):
    if request.user.is_authenticated:
        return redirect('assist_requests:request_list')

    total_users = CustomUser.objects.filter(role='user').count()
    total_volunteers = CustomUser.objects.filter(role='volunteer').count()
    completed = Request.objects.filter(status='completed').count()
    open_requests = Request.objects.filter(status='open').order_by('-created_at')[:3]

    features = [
        {'icon': '💬', 'title': 'In-app Messaging', 'desc': 'Chat directly with your matched volunteer in a secure, request-tied conversation.'},
        {'icon': '🔔', 'title': 'Real-time Notifications', 'desc': 'Instant alerts when your request is accepted, completed, or you receive a new message.'},
        {'icon': '⭐', 'title': 'Feedback & Reviews', 'desc': 'Leave star ratings after each completed request to build a trustworthy community.'},
        {'icon': '📊', 'title': 'Admin Analytics', 'desc': 'Admins get a full dashboard with Chart.js analytics, user stats, and platform insights.'},
    ]

    return render(request, 'home.html', {
        'total_users': total_users,
        'total_volunteers': total_volunteers,
        'completed': completed,
        'open_requests': open_requests,
        'features': features,
    })


urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('requests/', include('assist_requests.urls')),
    path('messaging/', include('messaging.urls')),
    path('notifications/', include('notifications.urls')),
    path('feedback/', include('feedback.urls')),
    path('rewards/', include('rewards.urls')),
    path('dashboard/', include('dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
