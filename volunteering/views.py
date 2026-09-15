from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Avg, Count
from assistance.models import AssistanceRequest, Feedback
from rewards.models import BadgeAward, Certificate
from .models import Skill, Availability

@login_required
def dashboard(request):
    """Volunteer dashboard with complete context"""
    if request.user.role != "volunteer":
        return redirect("user_dashboard")
    
    user = request.user
    tasks = AssistanceRequest.objects.filter(volunteer=user).select_related("seeker").order_by("-scheduled_at")
    
    # Get stats
    tasks_completed = tasks.filter(status=AssistanceRequest.Status.COMPLETED).count()
    rating_average = Feedback.objects.filter(volunteer=user).aggregate(Avg("rating"))["rating__avg"] or 0
    badges = BadgeAward.objects.filter(volunteer=user)
    available_requests = AssistanceRequest.objects.filter(volunteer__isnull=True, status=AssistanceRequest.Status.PENDING).order_by("-priority", "scheduled_at")
    
    context = {
        "tasks": tasks,
        "tasks_completed": tasks_completed,
        "total_requests": tasks.count(),
        "rating_average": round(rating_average, 2),
        "badges": badges,
        "available_requests": available_requests,
    }
    return render(request, "volunteer/dashboard.html", context)

@login_required
def accepted_requests(request):
    """View accepted/assigned requests"""
    tasks = AssistanceRequest.objects.filter(volunteer=request.user).select_related("seeker").order_by("-scheduled_at")
    return render(request, "volunteer/accepted-requests.html", {"tasks": tasks, "total_requests": tasks.count()})

@login_required
def accept_request(request, request_id):
    obj = get_object_or_404(AssistanceRequest, pk=request_id, status__in=[AssistanceRequest.Status.PENDING, AssistanceRequest.Status.MATCHED])
    if obj.volunteer_id in (None, request.user.id):
        obj.volunteer = request.user
        obj.status = AssistanceRequest.Status.ACCEPTED
        obj.save(update_fields=["volunteer", "status"])
    return redirect("accepted_requests")

@login_required
def complete_request(request, request_id):
    """Mark an assistance request as completed"""
    if request.method != "POST":
        return redirect("accepted_requests")
    
    assistance_request = get_object_or_404(
        AssistanceRequest,
        pk=request_id,
        volunteer=request.user,
        status=AssistanceRequest.Status.ACCEPTED
    )
    
    assistance_request.status = AssistanceRequest.Status.COMPLETED
    assistance_request.completed_at = timezone.now()
    assistance_request.save()
    
    return redirect("accepted_requests")

@login_required
def skills(request): return render(request,"volunteer/skills.html")
@login_required
def availability(request): return render(request,"volunteer/availability.html")
@login_required
def rewards(request):
    badges = BadgeAward.objects.filter(volunteer=request.user).select_related("badge")
    certificates = Certificate.objects.filter(volunteer=request.user)
    return render(request, "volunteer/rewards.html", {"badges": badges, "certificates": certificates})
@login_required
def chat(request):
    from chat.models import Conversation
    conversations = Conversation.objects.filter(
        request__volunteer=request.user
    ).select_related("request__seeker").order_by("-created_at")
    return render(request, "volunteer/chat.html", {"conversations": conversations})
@login_required
def profile(request): return render(request,"volunteer/profile.html")
