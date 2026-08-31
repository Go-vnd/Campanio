from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from assistance.models import AssistanceRequest
from .models import Skill, Availability

@login_required
def dashboard(request):
    tasks = AssistanceRequest.objects.filter(volunteer=request.user).order_by("-scheduled_at")
    return render(request, "volunteer/dashboard.html", {"tasks": tasks})

@login_required
def accepted_requests(request):
    tasks = AssistanceRequest.objects.filter(volunteer=request.user).order_by("-scheduled_at")
    return render(request, "volunteer/accepted-requests.html", {"tasks": tasks})

@login_required
def accept_request(request, request_id):
    obj = get_object_or_404(AssistanceRequest, pk=request_id, status__in=[AssistanceRequest.Status.PENDING, AssistanceRequest.Status.MATCHED])
    if obj.volunteer_id in (None, request.user.id):
        obj.volunteer = request.user
        obj.status = AssistanceRequest.Status.ACCEPTED
        obj.save(update_fields=["volunteer", "status"])
    return redirect("accepted_requests")

@login_required
def skills(request): return render(request,"volunteer/skills.html")
@login_required
def availability(request): return render(request,"volunteer/availability.html")
@login_required
def rewards(request): return render(request,"volunteer/rewards.html")
@login_required
def chat(request): return render(request,"volunteer/chat.html")
@login_required
def profile(request): return render(request,"volunteer/profile.html")
