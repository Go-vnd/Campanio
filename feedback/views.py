from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Review
from assist_requests.models import Request
from notifications.models import Notification


@login_required
def submit_feedback(request, request_id):
    assist_request = get_object_or_404(Request, pk=request_id, status='completed')

    # Only the requester can leave feedback for the volunteer
    if request.user != assist_request.user:
        messages.error(request, 'Only the requester can leave feedback.')
        return redirect('assist_requests:request_detail', pk=request_id)

    # Prevent duplicate reviews
    if assist_request.reviews.filter(reviewer=request.user).exists():
        messages.warning(request, 'You have already submitted feedback for this request.')
        return redirect('assist_requests:request_detail', pk=request_id)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comments = request.POST.get('comments', '')
        reviewee = assist_request.volunteer

        if reviewee and rating:
            Review.objects.create(
                request=assist_request,
                reviewer=request.user,
                reviewee=reviewee,
                rating=int(rating),
                comments=comments,
            )
            # Notify the volunteer
            Notification.objects.create(
                user=reviewee,
                message=f'{request.user.username} left you a {rating}⭐ review on "{assist_request.title}"!'
            )
            messages.success(request, 'Feedback submitted successfully! Thank you.')
        return redirect('assist_requests:request_detail', pk=request_id)

    return render(request, 'feedback/submit_feedback.html', {'assist_request': assist_request})
