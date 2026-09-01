from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Avg, Count
from .forms import RegisterForm, ProfileForm
from .models import Profile, User
from assistance.models import AssistanceRequest, Feedback
from rewards.models import BadgeAward

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            return redirect("/accounts/dashboard/")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})

@login_required
def dashboard(request):
    """Route to appropriate dashboard based on user role"""
    if request.user.role == "admin": 
        return redirect("admin_dashboard")
    if request.user.role == "volunteer": 
        return redirect("volunteer_dashboard")
    return redirect("user_dashboard")

@login_required
def user_dashboard(request):
    """User (seeker) dashboard with requests and stats"""
    user = request.user
    
    # Get user's assistance requests
    requests = AssistanceRequest.objects.filter(seeker=user).select_related("volunteer").order_by("-created_at")
    
    context = {
        "total_requests": requests.count(),
        "pending_requests": requests.filter(status="pending").count(),
        "accepted_requests": requests.filter(status="accepted").count(),
        "completed_requests": requests.filter(status="completed").count(),
        "recent_requests": requests[:5],
        "avg_rating_given": Feedback.objects.filter(seeker=user).aggregate(Avg("rating"))["rating__avg"] or 0,
    }
    return render(request, "user/dashboard.html", context)

@login_required
def profile(request):
    """User profile management"""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile)
    
    template_name = "volunteer/profile.html" if request.user.role == "volunteer" else "user/profile.html"
    return render(request, template_name, {"form": form})

@login_required
def create_request(request):
    """Create a new assistance request"""
    from assistance.forms import AssistanceRequestForm
    
    if request.method == "POST":
        form = AssistanceRequestForm(request.POST)
        if form.is_valid():
            assistance_request = form.save(commit=False)
            assistance_request.seeker = request.user
            assistance_request.save()
            messages.success(request, "Assistance request created successfully!")
            return redirect("request_history")
    else:
        form = AssistanceRequestForm()
    
    return render(request, "user/create-request.html", {"form": form})

@login_required
def request_history(request):
    """View user's request history"""
    if request.user.role == "volunteer":
        requests = AssistanceRequest.objects.filter(volunteer=request.user).select_related("seeker").order_by("-created_at")
    else:
        requests = AssistanceRequest.objects.filter(seeker=request.user).select_related("volunteer").order_by("-created_at")
    
    context = {
        "requests": requests,
        "pending_requests": requests.filter(status="pending").count(),
        "accepted_requests": requests.filter(status="accepted").count(),
        "completed_requests": requests.filter(status="completed").count(),
    }
    return render(request, "user/request-history.html", context)

@login_required
def feedback(request, request_id):
    """Submit feedback for completed request"""
    from assistance.forms import FeedbackForm
    
    assistance_request = get_object_or_404(AssistanceRequest, pk=request_id)
    
    # Only seeker can leave feedback
    if request.user != assistance_request.seeker:
        messages.error(request, "You can only leave feedback for requests you created.")
        return redirect("request_history")
    
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback_obj = form.save(commit=False)
            feedback_obj.seeker = request.user
            feedback_obj.volunteer = assistance_request.volunteer
            feedback_obj.request = assistance_request
            feedback_obj.save()
            messages.success(request, "Thank you for your feedback!")
            return redirect("request_history")
    else:
        form = FeedbackForm()
    
    return render(request, "user/feedback.html", {"form": form, "request": assistance_request})

@login_required
def user_chat(request):
    """User messaging/chat interface"""
    from chat.models import Conversation
    
    # Get conversations related to user's assistance requests
    if request.user.role == "volunteer":
        conversations = Conversation.objects.filter(
            request__volunteer=request.user
        ).select_related("request__seeker").order_by("-created_at")
    else:
        conversations = Conversation.objects.filter(
            request__seeker=request.user
        ).select_related("request__volunteer").order_by("-created_at")
    
    context = {
        "conversations": conversations,
    }
    return render(request, "user/chat.html", context)

@login_required
def user_notifications(request):
    """User notifications view"""
    from notifications.models import Notification
    
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    
    context = {
        "notifications": notifications,
        "unread_count": notifications.filter(is_read=False).count(),
    }
    return render(request, "user/notifications.html", context)
