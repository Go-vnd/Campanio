from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Message
from assist_requests.models import Request
from notifications.models import Notification


@login_required
def inbox(request):
    """Show all request-based conversations the user is part of."""
    conversations = Request.objects.filter(
        Q(user=request.user) | Q(volunteer=request.user),
        status__in=['assigned', 'completed']
    ).order_by('-updated_at')

    return render(request, 'messaging/inbox.html', {'conversations': conversations})


@login_required
def chat(request, request_id):
    assist_request = get_object_or_404(Request, pk=request_id)
    messages_qs = Message.objects.filter(request=assist_request).order_by('timestamp')

    # Only allow participants to view/send messages
    is_participant = (request.user == assist_request.user or request.user == assist_request.volunteer)

    if request.method == 'POST' and is_participant:
        content = request.POST.get('content', '').strip()
        if content and assist_request.status in ('assigned', 'completed'):
            # Determine receiver
            if request.user == assist_request.user:
                receiver = assist_request.volunteer
            else:
                receiver = assist_request.user

            if receiver:
                Message.objects.create(
                    sender=request.user,
                    receiver=receiver,
                    request=assist_request,
                    content=content,
                )
                # Create notification for receiver
                Notification.objects.create(
                    user=receiver,
                    message=f'New message from {request.user.username} on "{assist_request.title}"'
                )
        return redirect('messaging:chat', request_id=request_id)

    return render(request, 'messaging/chat.html', {
        'assist_request': assist_request,
        'messages': messages_qs,
        'is_participant': is_participant,
    })
