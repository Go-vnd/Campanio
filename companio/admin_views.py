import csv
import uuid
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import ContactMessage, Profile, User
from assistance.models import AssistanceRequest, Feedback
from rewards.models import Badge, BadgeAward, Certificate
from volunteering.models import Skill


def admin_required(view):
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.role != "admin" and not request.user.is_staff and not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


@admin_required
def admin_dashboard(request):
    """Admin dashboard with system overview, dynamic metrics, chart trends, and live verification queue"""
    if request.method == "POST":
        action = request.POST.get("action")
        target_id = request.POST.get("target_id")

        if action == "approve_volunteer":
            vol = get_object_or_404(User, pk=target_id, role="volunteer")
            vol.is_verified = True
            vol.save()
            profile, _ = Profile.objects.get_or_create(user=vol)
            profile.background_verified = True
            profile.save()
            messages.success(request, f"Volunteer '{vol.get_full_name() or vol.username}' verified and approved!")
            return redirect("admin_dashboard")

        elif action == "reject_volunteer":
            vol = get_object_or_404(User, pk=target_id, role="volunteer")
            vol.is_verified = False
            vol.save()
            profile, _ = Profile.objects.get_or_create(user=vol)
            profile.background_verified = False
            profile.save()
            messages.warning(request, f"Volunteer '{vol.get_full_name() or vol.username}' marked as unverified.")
            return redirect("admin_dashboard")

        elif action == "approve_skill":
            skill = get_object_or_404(Skill, pk=target_id)
            skill.verified = True
            skill.save()
            messages.success(request, f"Skill '{skill.name}' for {skill.volunteer.get_full_name() or skill.volunteer.username} approved!")
            return redirect("admin_dashboard")

        elif action == "reject_skill":
            skill = get_object_or_404(Skill, pk=target_id)
            skill.delete()
            messages.info(request, f"Skill '{skill.name}' was rejected and removed.")
            return redirect("admin_dashboard")

    # Metrics
    total_users = User.objects.filter(role="seeker").count()
    total_volunteers = User.objects.filter(role="volunteer").count()
    total_requests = AssistanceRequest.objects.count()
    pending_requests = AssistanceRequest.objects.filter(status="pending").count()
    completed_requests = AssistanceRequest.objects.filter(status="completed").count()
    total_badges = Badge.objects.count()
    unread_messages = ContactMessage.objects.filter(is_resolved=False).count()

    # Pending volunteer & skill verifications
    pending_volunteers = User.objects.filter(
        role="volunteer",
        is_verified=False
    ).prefetch_related("skills").order_by("-date_joined")

    pending_skills = Skill.objects.filter(
        verified=False
    ).select_related("volunteer").order_by("-id")

    # Monthly Trends Calculation for the last 6 months
    now = timezone.now()
    month_labels = []
    requests_monthly_data = []
    volunteers_monthly_data = []

    for i in range(5, -1, -1):
        # Calculate month date ranges
        m_date = now - timedelta(days=i * 30)
        m_name = m_date.strftime("%b")
        month_labels.append(m_name)
        m_year = m_date.year
        m_month = m_date.month

        req_count = AssistanceRequest.objects.filter(
            created_at__year=m_year,
            created_at__month=m_month
        ).count()
        vol_count = User.objects.filter(
            role="volunteer",
            date_joined__year=m_year,
            date_joined__month=m_month
        ).count()

        requests_monthly_data.append(req_count)
        volunteers_monthly_data.append(vol_count)

    # Category breakdown for chart
    categories_data = list(
        AssistanceRequest.objects.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    cat_labels = [c["category"].title() if c["category"] else "General" for c in categories_data]
    cat_counts = [c["count"] for c in categories_data]

    context = {
        "total_users": total_users,
        "total_volunteers": total_volunteers,
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "completed_requests": completed_requests,
        "total_badges": total_badges,
        "unread_messages": unread_messages,
        "pending_volunteers": pending_volunteers,
        "pending_skills": pending_skills,
        "month_labels": month_labels,
        "requests_monthly_data": requests_monthly_data,
        "volunteers_monthly_data": volunteers_monthly_data,
        "cat_labels": cat_labels,
        "cat_counts": cat_counts,
        "recent_requests": AssistanceRequest.objects.select_related("seeker", "volunteer").order_by("-created_at")[:5],
        "recent_feedback": Feedback.objects.select_related("volunteer", "seeker").order_by("-created_at")[:5],
    }
    return render(request, "admin/dashboard.html", context)


@admin_required
def admin_users(request):
    """Seeker user management with dynamic search, filter, and detail modal"""
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    users = User.objects.filter(role="seeker").select_related("profile").annotate(
        request_count=Count("assistance_requests"),
        completed_count=Count("assistance_requests", filter=Q(assistance_requests__status="completed"))
    ).order_by("-date_joined")

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    if status == "active":
        users = users.filter(is_active=True)
    elif status == "suspended":
        users = users.filter(is_active=False)
    elif status == "verified":
        users = users.filter(is_verified=True)
    elif status == "pending":
        users = users.filter(is_verified=False)

    context = {
        "users": users,
        "total_users": users.count(),
        "active_users": users.filter(is_active=True).count(),
        "query": query,
        "selected_status": status,
    }
    return render(request, "admin/users.html", context)


@admin_required
def admin_users_export(request):
    """Stream all seeker records into a CSV file for download"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="companio_users.csv"'

    writer = csv.writer(response)
    writer.writerow(["User ID", "Username", "First Name", "Last Name", "Email", "Phone", "Accessibility Preference", "Total Requests", "Joined Date", "Is Active", "Is Verified"])

    users = User.objects.filter(role="seeker").select_related("profile").annotate(
        request_count=Count("assistance_requests")
    ).order_by("-date_joined")

    for u in users:
        pref = u.profile.accessibility_preferences.get("preference", "standard") if hasattr(u, "profile") and u.profile else "standard"
        writer.writerow([
            f"USR-{u.id}",
            u.username,
            u.first_name,
            u.last_name,
            u.email,
            u.phone,
            pref,
            u.request_count,
            u.date_joined.strftime("%Y-%m-%d %H:%M"),
            "Active" if u.is_active else "Suspended",
            "Verified" if u.is_verified else "Pending"
        ])

    return response


@admin_required
def admin_user_toggle(request, user_id):
    """Toggle user active status (Suspend / Activate)"""
    if request.method == "POST":
        user = get_object_or_404(User, pk=user_id)
        if user == request.user:
            messages.error(request, "You cannot suspend your own admin account.")
        else:
            user.is_active = not user.is_active
            user.save()
            status_str = "activated" if user.is_active else "suspended"
            messages.success(request, f"User '{user.username}' has been {status_str}.")
    return redirect("admin_users")


@admin_required
def admin_volunteers(request):
    """Volunteer management with search, filters, verification toggle, certificate issuance, and badge awards"""
    query = request.GET.get("q", "").strip()
    verification = request.GET.get("verification", "").strip()
    skill_filter = request.GET.get("skill", "").strip()

    volunteers = User.objects.filter(role="volunteer").select_related("profile").prefetch_related("skills").annotate(
        completed_tasks=Count("accepted_requests", filter=Q(accepted_requests__status="completed")),
        avg_rating=Avg("received_feedback__rating"),
    ).order_by("-date_joined")

    if query:
        volunteers = volunteers.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(skills__name__icontains=query)
        ).distinct()

    if verification == "verified":
        volunteers = volunteers.filter(Q(is_verified=True) | Q(profile__background_verified=True))
    elif verification == "pending":
        volunteers = volunteers.filter(is_verified=False, profile__background_verified=False)

    if skill_filter:
        volunteers = volunteers.filter(skills__name__icontains=skill_filter).distinct()

    all_badges = Badge.objects.filter(active=True)

    context = {
        "volunteers": volunteers,
        "total_volunteers": volunteers.count(),
        "active_volunteers": volunteers.filter(is_active=True).count(),
        "all_badges": all_badges,
        "query": query,
        "selected_verification": verification,
        "selected_skill": skill_filter,
    }
    return render(request, "admin/volunteers.html", context)


@admin_required
def admin_volunteer_toggle_verify(request, user_id):
    """Toggle volunteer background verification status"""
    if request.method == "POST":
        volunteer = get_object_or_404(User, pk=user_id, role="volunteer")
        profile, _ = Profile.objects.get_or_create(user=volunteer)
        
        # Toggle
        new_status = not (volunteer.is_verified and profile.background_verified)
        volunteer.is_verified = new_status
        volunteer.save()
        profile.background_verified = new_status
        profile.save()

        status_text = "Verified & Cleared" if new_status else "Marked as Pending"
        messages.success(request, f"Volunteer '{volunteer.get_full_name() or volunteer.username}' is now {status_text}.")
    return redirect("admin_volunteers")


@admin_required
def admin_issue_certificate(request, user_id):
    """Issue a digital recognition certificate to a volunteer"""
    if request.method == "POST":
        volunteer = get_object_or_404(User, pk=user_id, role="volunteer")
        title = request.POST.get("title", "Certificate of Community Excellence").strip()
        hours = request.POST.get("hours", "10").strip()
        
        try:
            hours_val = float(hours)
        except ValueError:
            hours_val = 10.0

        cert_id = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        Certificate.objects.create(
            volunteer=volunteer,
            title=title or "Certificate of Community Excellence",
            hours_recognized=hours_val,
            certificate_id=cert_id
        )
        messages.success(request, f"Certificate '{title}' (ID: {cert_id}) successfully issued to {volunteer.get_full_name() or volunteer.username}!")
    return redirect("admin_volunteers")


@admin_required
def admin_award_volunteer_badge(request, user_id):
    """Award a specific badge to a volunteer"""
    if request.method == "POST":
        volunteer = get_object_or_404(User, pk=user_id, role="volunteer")
        badge_id = request.POST.get("badge_id")
        badge = get_object_or_404(Badge, pk=badge_id)
        
        BadgeAward.objects.create(volunteer=volunteer, badge=badge)
        messages.success(request, f"Badge '{badge.title}' awarded to {volunteer.get_full_name() or volunteer.username}!")
    return redirect("admin_volunteers")


@admin_required
def admin_requests(request):
    """Assistance request management with search, filter, and volunteer assignment"""
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    category = request.GET.get("category", "").strip()

    requests_all = AssistanceRequest.objects.select_related("seeker", "volunteer").order_by("-created_at")

    if query:
        requests_all = requests_all.filter(
            Q(id__icontains=query.replace("#REQ-", "").replace("REQ-", "")) |
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(seeker__username__icontains=query) |
            Q(seeker__first_name__icontains=query) |
            Q(seeker__last_name__icontains=query) |
            Q(volunteer__first_name__icontains=query) |
            Q(volunteer__last_name__icontains=query)
        )

    if status:
        requests_all = requests_all.filter(status=status)
    if priority:
        requests_all = requests_all.filter(priority=priority)
    if category:
        requests_all = requests_all.filter(category=category)

    # Active volunteers for re-assignment dropdown
    volunteers = User.objects.filter(role="volunteer", is_active=True).order_by("first_name", "last_name")

    context = {
        "requests": requests_all,
        "total_requests": requests_all.count(),
        "pending_requests": requests_all.filter(status="pending").count(),
        "accepted_requests": requests_all.filter(status="accepted").count(),
        "completed_requests": requests_all.filter(status="completed").count(),
        "volunteers": volunteers,
        "query": query,
        "selected_status": status,
        "selected_priority": priority,
        "selected_category": category,
    }
    return render(request, "admin/requests.html", context)


@admin_required
def admin_request_assign(request, request_id):
    """Assign/reassign volunteer and update status for an assistance request"""
    if request.method == "POST":
        req_obj = get_object_or_404(AssistanceRequest, pk=request_id)
        volunteer_id = request.POST.get("volunteer_id")
        new_status = request.POST.get("status")

        if volunteer_id == "unassigned" or not volunteer_id:
            req_obj.volunteer = None
            if req_obj.status == "accepted":
                req_obj.status = "pending"
        else:
            vol = get_object_or_404(User, pk=volunteer_id, role="volunteer")
            req_obj.volunteer = vol
            if req_obj.status == "pending":
                req_obj.status = "accepted"

        if new_status and new_status in dict(AssistanceRequest.Status.choices):
            req_obj.status = new_status
            if new_status == "completed" and not req_obj.completed_at:
                req_obj.completed_at = timezone.now()

        req_obj.save()
        messages.success(request, f"Request #REQ-{req_obj.id} successfully updated!")
    return redirect("admin_requests")


@admin_required
def admin_analytics(request):
    """System analytics and detailed reports"""
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
    total_certificates = Certificate.objects.count()

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
        "total_certificates": total_certificates,
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
    """Badge and certificate management with creation, toggle, deletion, and manual awards"""
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
        elif action == "award":
            badge_id = request.POST.get("badge_id")
            volunteer_id = request.POST.get("volunteer_id")
            badge = get_object_or_404(Badge, pk=badge_id)
            volunteer = get_object_or_404(User, pk=volunteer_id, role="volunteer")
            BadgeAward.objects.create(badge=badge, volunteer=volunteer)
            messages.success(request, f"Badge '{badge.title}' awarded to {volunteer.get_full_name() or volunteer.username}!")

        return redirect("admin_badges")

    badges = Badge.objects.annotate(
        awarded_count=Count("badge_awards")
    ).order_by("-id")

    recent_awards = BadgeAward.objects.select_related("badge", "volunteer").order_by("-awarded_at")[:15]
    total_awards = BadgeAward.objects.count()
    total_certificates = Certificate.objects.count()
    volunteers = User.objects.filter(role="volunteer", is_active=True).order_by("first_name", "last_name")

    context = {
        "badges": badges,
        "total_badges": badges.count(),
        "total_awards": total_awards,
        "total_certificates": total_certificates,
        "recent_awards": recent_awards,
        "volunteers": volunteers,
    }
    return render(request, "admin/badges.html", context)


@admin_required
def admin_contact_messages(request):
    """View and resolve support and contact inquiries"""
    if request.method == "POST":
        msg_id = request.POST.get("message_id")
        action = request.POST.get("action")
        contact_msg = get_object_or_404(ContactMessage, pk=msg_id)

        if action == "toggle_resolve":
            contact_msg.is_resolved = not contact_msg.is_resolved
            contact_msg.save()
            status_text = "marked as resolved" if contact_msg.is_resolved else "marked as open"
            messages.success(request, f"Inquiry #{contact_msg.id} {status_text}.")
        elif action == "delete":
            contact_msg.delete()
            messages.success(request, f"Inquiry #{msg_id} deleted.")
        return redirect("admin_contact_messages")

    filter_status = request.GET.get("status", "")
    inquiries = ContactMessage.objects.order_by("-created_at")

    if filter_status == "pending":
        inquiries = inquiries.filter(is_resolved=False)
    elif filter_status == "resolved":
        inquiries = inquiries.filter(is_resolved=True)

    context = {
        "inquiries": inquiries,
        "total_inquiries": ContactMessage.objects.count(),
        "unresolved_inquiries": ContactMessage.objects.filter(is_resolved=False).count(),
        "selected_status": filter_status,
    }
    return render(request, "admin/contact_messages.html", context)
