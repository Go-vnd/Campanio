from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.db.models import Count, Avg, Q
from accounts.models import User
from assistance.models import AssistanceRequest, Feedback
from rewards.models import Badge, BadgeAward
from volunteering.models import Skill

def admin_required(view):
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.role != "admin" and not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped

@admin_required
def admin_dashboard(request):
    """Admin dashboard with system overview"""
    context = {
        "total_users": User.objects.filter(role="seeker").count(),
        "total_volunteers": User.objects.filter(role="volunteer").count(),
        "total_requests": AssistanceRequest.objects.count(),
        "pending_requests": AssistanceRequest.objects.filter(status="pending").count(),
        "completed_requests": AssistanceRequest.objects.filter(status="completed").count(),
        "total_badges": Badge.objects.count(),
        "recent_requests": AssistanceRequest.objects.select_related("seeker", "volunteer").order_by("-created_at")[:5],
        "recent_feedback": Feedback.objects.select_related("volunteer", "seeker").order_by("-created_at")[:5],
    }
    return render(request, "admin/dashboard.html", context)

@admin_required
def admin_users(request):
    """User management dashboard"""
    users = User.objects.filter(role="seeker").annotate(
        request_count=Count("assistance_requests")
    ).order_by("-created_at")
    
    context = {
        "users": users,
        "total_users": users.count(),
        "active_users": users.filter(is_active=True).count(),
    }
    return render(request, "admin/users.html", context)

@admin_required
def admin_volunteers(request):
    """Volunteer management dashboard"""
    volunteers = User.objects.filter(role="volunteer").annotate(
        completed_tasks=Count("accepted_requests", filter=Q(accepted_requests__status="completed")),
        avg_rating=Avg("received_feedback__rating"),
    ).order_by("-created_at")
    
    context = {
        "volunteers": volunteers,
        "total_volunteers": volunteers.count(),
        "active_volunteers": volunteers.filter(is_active=True).count(),
        "badges": BadgeAward.objects.all(),  # For template
    }
    return render(request, "admin/volunteers.html", context)

@admin_required
def admin_requests(request):
    """Assistance request management"""
    requests_all = AssistanceRequest.objects.select_related("seeker", "volunteer").order_by("-created_at")
    
    context = {
        "requests": requests_all,
        "total_requests": requests_all.count(),
        "pending_requests": requests_all.filter(status="pending").count(),
        "accepted_requests": requests_all.filter(status="accepted").count(),
        "completed_requests": requests_all.filter(status="completed").count(),
    }
    return render(request, "admin/requests.html", context)

@admin_required
def admin_analytics(request):
    """System analytics and reports"""
    context = {
        "total_users": User.objects.filter(role="seeker").count(),
        "total_volunteers": User.objects.filter(role="volunteer").count(),
        "total_requests": AssistanceRequest.objects.count(),
        "avg_rating": Feedback.objects.aggregate(Avg("rating"))["rating__avg"] or 0,
        "completion_rate": (AssistanceRequest.objects.filter(status="completed").count() / 
                           AssistanceRequest.objects.count() * 100) if AssistanceRequest.objects.count() > 0 else 0,
        "requests_by_category": AssistanceRequest.objects.values("category").annotate(count=Count("id")).order_by("-count"),
        "volunteers_by_skill": Skill.objects.annotate(volunteer_count=Count("volunteers")).order_by("-volunteer_count")[:10],
        "user_growth": User.objects.filter(role="seeker").values("created_at__month").annotate(count=Count("id")).order_by("created_at__month"),
    }
    return render(request, "admin/analytics.html", context)

@admin_required
def admin_badges(request):
    """Badge and certificate management"""
    badges = Badge.objects.annotate(
        awarded_count=Count("badge_awards")
    ).order_by("-awarded_count")
    
    context = {
        "badges": badges,
        "total_badges": badges.count(),
        "total_awards": BadgeAward.objects.count(),
    }
    return render(request, "admin/badges.html", context)
