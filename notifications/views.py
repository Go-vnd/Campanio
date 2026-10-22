from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def notification_list(request):
    notifs = request.user.notifications.all()
    # Mark all as read when viewed
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications/notification_list.html', {'notifications': notifs})


@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    return redirect('notifications:notification_list')
