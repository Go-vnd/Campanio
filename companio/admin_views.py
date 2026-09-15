from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Avg, Q
from accounts.models import User
from assistance.models import AssistanceRequest, Feedback
from rewards.models import Badge, BadgeAward, Certificate
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
    ).order_by("-date_joined")
    
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
    ).order_by("-date_joined")
    
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
    total_seekers = User.objects.filter(role="seeker").count()
    total_volunteers = User.objects.filter(role="volunteer").count()
    total_requests = AssistanceRequest.objects.count()
    completed_requests = AssistanceRequest.objects.filter(status="completed").count()
    pending_requests = AssistanceRequest.objects.filter(status="pending").count()
    accepted_requests = AssistanceRequest.objects.filter(status="accepted").count()
    
    completion_rate = round((completed_requests / total_requests * 100), 1) if total_requests > 0 else 0
    avg_rating = Feedback.objects.aggregate(Avg("rating"))["rating__avg"] or 0
    avg_rating = round(avg_rating, 1)
    total_feedbacks = Feedback.objects.count()
    total_badges_awarded = BadgeAward.objects.count()

    requests_by_category = list(
        AssistanceRequest.objects.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    
    volunteers_by_skill = list(
        Skill.objects.values("name")
        .annotate(volunteer_count=Count("volunteer", distinct=True))
        .order_by("-volunteer_count")[:10]
    )
    
    rating_5 = Feedback.objects.filter(rating=5).count()
    rating_4 = Feedback.objects.filter(rating=4).count()
    rating_3 = Feedback.objects.filter(rating=3).count()
    rating_2 = Feedback.objects.filter(rating=2).count()
    rating_1 = Feedback.objects.filter(rating=1).count()

    context = {
        "total_users": total_seekers,
        "total_volunteers": total_volunteers,
        "total_requests": total_requests,
        "completed_requests": completed_requests,
        "pending_requests": pending_requests,
        "accepted_requests": accepted_requests,
        "completion_rate": completion_rate,
        "avg_rating": avg_rating,
        "total_feedbacks": total_feedbacks,
        "total_badges_awarded": total_badges_awarded,
        "requests_by_category": requests_by_category,
        "volunteers_by_skill": volunteers_by_skill,
        "rating_5": rating_5,
        "rating_4": rating_4,
        "rating_3": rating_3,
        "rating_2": rating_2,
        "rating_1": rating_1,
    }
    return render(request, "admin/analytics.html", context)

@admin_required
def admin_badges(request):
    """Badge and certificate management"""
    if request.method == "POST":
        action = request.POST.get("action", "create")
        if action == "create":
            title = request.POST.get("title", "").strip()
            criteria = request.POST.get("criteria", "").strip()
            if title and criteria:
                Badge.objects.create(title=title, criteria=criteria, active=True)
                messages.success(request, f"Badge '{title}' created successfully!")
            else:
                messages.error(request, "Badge title and criteria are required.")
        elif action == "toggle":
            badge_id = request.POST.get("badge_id")
            badge = Badge.objects.filter(id=badge_id).first()
            if badge:
                badge.active = not badge.active
                badge.save()
                status_text = "activated" if badge.active else "deactivated"
                messages.info(request, f"Badge '{badge.title}' has been {status_text}.")
        elif action == "delete":
            badge_id = request.POST.get("badge_id")
            badge = Badge.objects.filter(id=badge_id).first()
            if badge:
                title = badge.title
                badge.delete()
                messages.success(request, f"Badge '{title}' deleted successfully.")
        return redirect("admin_badges")

    badges = Badge.objects.annotate(
        awarded_count=Count("badge_awards")
    ).order_by("-id")

    recent_awards = BadgeAward.objects.select_related("badge", "volunteer").order_by("-awarded_at")[:10]
    total_awards = BadgeAward.objects.count()
    total_certificates = Certificate.objects.count()

    context = {
        "badges": badges,
        "total_badges": badges.count(),
        "total_awards": total_awards,
        "total_certificates": total_certificates,
        "recent_awards": recent_awards,
    }
    return render(request, "admin/badges.html", context)
