from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone

from .models import AssistanceRequest, Feedback


@login_required
def volunteer_dashboard(request):
    """Volunteer dashboard - only for volunteers"""
    if request.user.role != "volunteer":
        return redirect("user_dashboard")
    
    user = request.user

    # Requests already assigned to this volunteer
    tasks = (
        AssistanceRequest.objects
        .filter(volunteer=user)
        .select_related("seeker")
        .order_by("-scheduled_at")
    )

    # Completed tasks
    completed_tasks = tasks.filter(
        status=AssistanceRequest.Status.COMPLETED
    )

    # Number of completed tasks
    tasks_completed = completed_tasks.count()

    # Average rating received by volunteer
    rating_average = (
        Feedback.objects
        .filter(volunteer=user)
        .aggregate(average=Avg("rating"))["average"]
        or 0
    )

    # Number of feedback/reward-related records for now
    earned_badges = 0

    # Requests which are still available for volunteers
    available_requests = (
        AssistanceRequest.objects
        .filter(
            volunteer__isnull=True,
            status=AssistanceRequest.Status.PENDING
        )
        .order_by("-priority", "scheduled_at")
    )

    context = {
        "tasks": tasks,
        "tasks_completed": tasks_completed,
        "rating_average": round(rating_average, 2),
        "earned_badges": earned_badges,
        "available_requests": available_requests,
    }

    return render(
        request,
        "volunteer/dashboard.html",
        context
    )


@login_required
def accept_request(request, request_id):
    """Accept an assistance request"""
    if request.method != "POST":
        return redirect("volunteer_dashboard")

    assistance_request = get_object_or_404(
        AssistanceRequest,
        pk=request_id,
        volunteer__isnull=True,
        status=AssistanceRequest.Status.PENDING
    )

    assistance_request.volunteer = request.user
    assistance_request.status = AssistanceRequest.Status.ACCEPTED
    assistance_request.save()

    messages.success(
        request,
        "Assistance request accepted successfully!"
    )

    return redirect("volunteer_dashboard")


@login_required
def complete_request(request, request_id):
    """Mark an assistance request as completed"""
    if request.method != "POST":
        return redirect("volunteer_dashboard")

    assistance_request = get_object_or_404(
        AssistanceRequest,
        pk=request_id,
        volunteer=request.user
    )

    assistance_request.status = AssistanceRequest.Status.COMPLETED
    assistance_request.completed_at = timezone.now()
    assistance_request.save()

    messages.success(
        request,
        "Assistance request marked as completed."
    )

    return redirect("volunteer_dashboard")