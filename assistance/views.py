from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import datetime
from .forms import AssistanceRequestForm, FeedbackForm
from .models import AssistanceRequest, Feedback

@login_required
def create_request(request):
    if request.method == "POST":
        data=request.POST.copy(); d=data.get("scheduled_date"); tm=data.get("scheduled_time"); data["scheduled_at"]=f"{d} {tm}" if d and tm else ""; data["priority"]="urgent" if data.get("priority")=="urgent" else "normal"
        form=AssistanceRequestForm(data)
        if form.is_valid():
            obj=form.save(commit=False); obj.seeker=request.user; obj.save(); return redirect("request_history")
    else: form=AssistanceRequestForm()
    return render(request,"user/create-request.html",{"form":form})

@login_required
def request_history(request):
    qs = AssistanceRequest.objects.filter(seeker=request.user).select_related("volunteer")
    return render(request, "user/request-history.html", {"requests": qs})

@login_required
def feedback(request, request_id):
    obj = get_object_or_404(AssistanceRequest, pk=request_id, seeker=request.user, status=AssistanceRequest.Status.COMPLETED)
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid() and obj.volunteer:
            f = form.save(commit=False)
            f.request, f.seeker, f.volunteer = obj, request.user, obj.volunteer
            f.save()
            return redirect("request_history")
    else:
        form = FeedbackForm()
    return render(request, "user/feedback.html", {"request_obj": obj, "form": form})

@login_required
def user_chat(request): return render(request,"user/chat.html")
@login_required
def user_notifications(request): return render(request,"user/notifications.html")
@login_required
def user_profile(request): return render(request,"user/profile.html")
