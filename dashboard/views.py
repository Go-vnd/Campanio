import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.conf import settings

from accounts.models import CustomUser, Profile
from assist_requests.models import Request, Category
from feedback.models import Review
from messaging.models import Message
from .models import AdminAuditLog, Report, ReportNote, ReportStatusHistory

# ── Configurable thresholds (can be moved to settings later) ──────────────
UNASSIGNED_DAYS_THRESHOLD = 3   # "unassigned for more than N days"
LOW_RATING_THRESHOLD = 2        # 1-2 stars counts as "low"
LOW_RATING_RECENT_DAYS = 30     # look back window for recent low-rated volunteers
REPORTS_ATTENTION_COUNT = 1     # any unreviewed report triggers the strip
PAGE_SIZE = 25


def _qs_no_page(get_params):
    """Return URL-encoded query string with 'page' removed (for pagination links)."""
    d = get_params.copy()
    d.pop('page', None)
    return d.urlencode()


def _log(request, action, target_type, obj, reason=''):
    """Helper: write one row to the admin audit log."""
    AdminAuditLog.objects.create(
        staff=request.user,
        action=action,
        target_type=target_type,
        target_id=str(obj.pk),
        target_repr=str(obj),
        reason=reason,
    )


@staff_member_required
def dashboard_home(request):
    total_users = CustomUser.objects.filter(role='user').count()
    total_volunteers = CustomUser.objects.filter(role='volunteer').count()
    total_requests = Request.objects.count()
    open_requests = Request.objects.filter(status='open').count()
    assigned_requests = Request.objects.filter(status='assigned').count()
    completed_requests = Request.objects.filter(status='completed').count()
    cancelled_requests = Request.objects.filter(status='cancelled').count()
    total_reviews = Review.objects.count()
    recent_requests = Request.objects.select_related('user', 'volunteer').order_by('-created_at')[:10]

    # Top volunteers by points
    top_volunteers = Profile.objects.select_related('user').order_by('-points')[:5]

    # Chart.js data
    requests_status_data = json.dumps({
        'labels': ['Open', 'Assigned', 'Completed', 'Cancelled'],
        'data': [open_requests, assigned_requests, completed_requests, cancelled_requests],
    })

    # Requests per category
    categories = Category.objects.all()
    cat_labels = [c.name for c in categories]
    cat_counts = [Request.objects.filter(category=c).count() for c in categories]
    if not categories:
        cat_labels = ['Uncategorized']
        cat_counts = [total_requests]

    requests_category_data = json.dumps({
        'labels': cat_labels,
        'data': cat_counts,
    })

    # ── Phase 3 Reports Analytics ──────────────────────────────────────────
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    open_reports_count = Report.objects.filter(status__in=['new', 'in_review']).count()
    reports_this_month = Report.objects.filter(created_at__gte=month_start).count()

    # Average time to resolve (for resolved / dismissed reports with resolved_at)
    resolved_reports = Report.objects.filter(status__in=['resolved', 'action_taken', 'dismissed'], resolved_at__isnull=False)
    if resolved_reports.exists():
        total_seconds = sum((r.resolved_at - r.created_at).total_seconds() for r in resolved_reports)
        avg_hours = round(total_seconds / (3600 * resolved_reports.count()), 1)
        avg_resolve_time = f"{avg_hours}h"
    else:
        avg_resolve_time = "N/A"

    # Breakdown by type Chart.js
    type_counts = {}
    for code, label in Report.TYPE_CHOICES:
        type_counts[label] = Report.objects.filter(report_type=code).count()

    reports_type_data = json.dumps({
        'labels': list(type_counts.keys()),
        'data': list(type_counts.values()),
    })

    # ── Attention Needed panel ─────────────────────────────────────────────
    cutoff = timezone.now() - timedelta(days=UNASSIGNED_DAYS_THRESHOLD)
    low_rating_cutoff = timezone.now() - timedelta(days=LOW_RATING_RECENT_DAYS)

    high_priority_unassigned = Request.objects.filter(
        status='open', priority='High', volunteer__isnull=True
    ).count()

    stale_unassigned = Request.objects.filter(
        status='open', volunteer__isnull=True, created_at__lte=cutoff
    ).count()

    unverified_volunteers = CustomUser.objects.filter(
        role='volunteer', is_verified=False, is_active=True
    ).count()

    # Low-rated volunteers: those who received reviews ≤ LOW_RATING_THRESHOLD recently
    low_rated_volunteer_ids = (
        Review.objects
        .filter(rating__lte=LOW_RATING_THRESHOLD, created_at__gte=low_rating_cutoff)
        .values_list('reviewee_id', flat=True)
        .distinct()
    )
    low_rated_volunteers = CustomUser.objects.filter(
        pk__in=low_rated_volunteer_ids, role='volunteer'
    ).count()

    new_reports_count = Report.objects.filter(status='new').count()

    attention_items = [
        {
            'icon': 'bi-exclamation-triangle-fill',
            'color': 'var(--accent-pink)',
            'label': 'High-Priority Unassigned',
            'count': high_priority_unassigned,
            'url': '/dashboard/requests/?status=open&priority=High&unassigned=1',
            'empty_label': 'No urgent open requests',
        },
        {
            'icon': 'bi-clock-history',
            'color': 'var(--accent-amber)',
            'label': f'Unassigned >{UNASSIGNED_DAYS_THRESHOLD}d',
            'count': stale_unassigned,
            'url': f'/dashboard/requests/?status=open&unassigned=1&stale=1',
            'empty_label': 'No stale unassigned requests',
        },
        {
            'icon': 'bi-person-check-fill',
            'color': 'var(--accent-teal)',
            'label': 'Unverified Volunteers',
            'count': unverified_volunteers,
            'url': '/dashboard/users/?role=volunteer&verified=0',
            'empty_label': 'All volunteers verified',
        },
        {
            'icon': 'bi-flag-fill',
            'color': 'var(--accent-blue)',
            'label': 'New Reports',
            'count': new_reports_count,
            'url': '/dashboard/reports/?status=new',
            'empty_label': 'No new reports',
        },
        {
            'icon': 'bi-star-half',
            'color': 'var(--accent-purple)',
            'label': 'Recent Low-Rated Volunteers',
            'count': low_rated_volunteers,
            'url': f'/dashboard/users/?role=volunteer&low_rated=1',
            'empty_label': 'No low-rated volunteers recently',
        },
    ]

    # ── Phase 6: Suspicious Activity Detection ───────────────────────────────
    susp_cfg = getattr(settings, 'SUSPICIOUS_ACTIVITY_THRESHOLDS', {})
    pair_thresh = susp_cfg.get('PAIR_COMPLETIONS_THRESHOLD', 3)
    quick_mins = susp_cfg.get('QUICK_COMPLETION_MINUTES', 10)
    cluster_days = susp_cfg.get('NEW_ACCOUNT_CLUSTER_DAYS', 7)

    suspicious_flags = []

    # 1. Same user-volunteer pair completing many requests
    pair_completions = (
        Request.objects
        .filter(status='completed', volunteer__isnull=False)
        .values('user_id', 'user__username', 'volunteer_id', 'volunteer__username')
        .annotate(total=Count('id'))
        .filter(total__gte=pair_thresh)
        .order_by('-total')
    )
    for p in pair_completions:
        suspicious_flags.append({
            'type': 'Frequent Pair Collaboration',
            'severity': 'high' if p['total'] >= 5 else 'medium',
            'badge_color': '#ef4444' if p['total'] >= 5 else '#f59e0b',
            'summary': f"Requester @{p['user__username']} and Volunteer @{p['volunteer__username']} completed {p['total']} requests together.",
            'action_url': f"/dashboard/requests/?requester={p['user__username']}&volunteer={p['volunteer__username']}&status=completed",
            'action_label': 'View Requests'
        })

    # 2. Requests completed within minutes of acceptance
    quick_requests = Request.objects.filter(
        status='completed',
        accepted_at__isnull=False,
        completed_at__isnull=False
    ).select_related('user', 'volunteer')
    for qr in quick_requests:
        diff_mins = (qr.completed_at - qr.accepted_at).total_seconds() / 60.0
        if diff_mins <= quick_mins:
            suspicious_flags.append({
                'type': 'Rapid Task Completion',
                'severity': 'high',
                'badge_color': '#ef4444',
                'summary': f"Request #{qr.pk} ('{qr.title[:30]}') marked completed in {round(diff_mins, 1)}m by @{qr.volunteer.username if qr.volunteer else '?'}.",
                'action_url': f"/requests/{qr.pk}/",
                'action_label': 'Inspect Request'
            })

    # 3. Completed requests with no chat activity
    completed_reqs = Request.objects.filter(status='completed', volunteer__isnull=False).select_related('user', 'volunteer')[:25]
    for cr in completed_reqs:
        has_msgs = Message.objects.filter(request=cr).exists()
        if not has_msgs:
            suspicious_flags.append({
                'type': 'Zero Chat Communication',
                'severity': 'medium',
                'badge_color': '#f59e0b',
                'summary': f"Completed request #{cr.pk} ('{cr.title[:30]}') has 0 messages between @{cr.user.username} and @{cr.volunteer.username}.",
                'action_url': f"/requests/{cr.pk}/",
                'action_label': 'Inspect Request'
            })

    # 4. New account clusters interacting only with each other
    cluster_cutoff = timezone.now() - timedelta(days=cluster_days)
    new_users = CustomUser.objects.filter(date_joined__gte=cluster_cutoff)
    new_user_ids = set(new_users.values_list('pk', flat=True))
    cluster_reqs = Request.objects.filter(
        user_id__in=new_user_ids,
        volunteer_id__in=new_user_ids
    ).select_related('user', 'volunteer')[:10]
    for cr in cluster_reqs:
        suspicious_flags.append({
            'type': 'New Account Cluster Interaction',
            'severity': 'high',
            'badge_color': '#ef4444',
            'summary': f"New accounts @{cr.user.username} & @{cr.volunteer.username} (both created <{cluster_days}d ago) interacting on request #{cr.pk}.",
            'action_url': f"/dashboard/users/{cr.volunteer.pk}/",
            'action_label': 'View Volunteer'
        })

    # ── Phase 6: Supply / Demand Insights ────────────────────────────────────
    all_categories = Category.objects.all()
    active_volunteers = CustomUser.objects.filter(role='volunteer', is_active=True).select_related('volunteer_profile')
    all_vol_skills_raw = [
        v.volunteer_profile.skills.lower() for v in active_volunteers if hasattr(v, 'volunteer_profile') and v.volunteer_profile.skills
    ]

    # Categories with no active matching volunteers
    categories_without_volunteers = []
    for cat in all_categories:
        cat_term = cat.name.lower()
        has_match = any(cat_term in s for s in all_vol_skills_raw)
        if not has_match:
            categories_without_volunteers.append(cat.name)

    # Average time to acceptance by category
    acceptance_by_cat = []
    for cat in all_categories:
        cat_reqs = Request.objects.filter(category=cat, accepted_at__isnull=False)
        if cat_reqs.exists():
            total_sec = sum((r.accepted_at - r.created_at).total_seconds() for r in cat_reqs if r.accepted_at > r.created_at)
            avg_h = round(total_sec / (3600 * cat_reqs.count()), 1)
            acceptance_by_cat.append({'category': cat.name, 'avg_hours': avg_h})

    # Open requests no volunteer's skills match
    all_vol_skills_set = set()
    for s_raw in all_vol_skills_raw:
        for sk in s_raw.split(','):
            if sk.strip():
                all_vol_skills_set.add(sk.strip().lower())

    unmatched_open_requests = []
    for o_req in Request.objects.filter(status='open', volunteer__isnull=True):
        req_skills = [sk.strip().lower() for sk in o_req.required_skills.split(',') if sk.strip()]
        if req_skills and not any(sk in all_vol_skills_set for sk in req_skills):
            unmatched_open_requests.append(o_req)

    all_clear = all(item['count'] == 0 for item in attention_items)

    context = {
        'total_users': total_users,
        'total_volunteers': total_volunteers,
        'total_requests': total_requests,
        'open_requests': open_requests,
        'completed_requests': completed_requests,
        'total_reviews': total_reviews,
        'recent_requests': recent_requests,
        'top_volunteers': top_volunteers,
        'requests_status_data': requests_status_data,
        'requests_category_data': requests_category_data,
        # Phase 3 Reports statistics
        'open_reports_count': open_reports_count,
        'reports_this_month': reports_this_month,
        'avg_resolve_time': avg_resolve_time,
        'reports_type_data': reports_type_data,
        # Phase 6 Suspicious activity & Supply/Demand
        'suspicious_flags': suspicious_flags[:10],
        'categories_without_volunteers': categories_without_volunteers,
        'acceptance_by_cat': acceptance_by_cat,
        'unmatched_open_requests': unmatched_open_requests[:5],
        # Attention Needed
        'attention_items': attention_items,
        'all_clear': all_clear,
    }
    return render(request, 'dashboard/dashboard.html', context)


@staff_member_required
def manage_users(request):
    # ── POST: toggle active status ─────────────────────────────────────────
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        return_to = request.POST.get('return_to', '/dashboard/users/')
        user_obj = get_object_or_404(CustomUser, pk=user_id)
        if action == 'toggle_active':
            user_obj.is_active = not user_obj.is_active
            user_obj.save()
            verb = 'activate_user' if user_obj.is_active else 'deactivate_user'
            _log(request, verb, 'User', user_obj)
            label = 'activated' if user_obj.is_active else 'deactivated'
            messages.success(request, f"User \u201c{user_obj.username}\u201d {label}.")
        return redirect(return_to)

    # ── GET: build filtered queryset ───────────────────────────────────────
    qs = CustomUser.objects.select_related('volunteer_profile').all()

    role        = request.GET.get('role', '')
    active      = request.GET.get('active', '')
    verified    = request.GET.get('verified', '')
    q           = request.GET.get('q', '').strip()
    joined_from = request.GET.get('joined_from', '')
    joined_to   = request.GET.get('joined_to', '')
    tier        = request.GET.get('tier', '')
    low_rated   = request.GET.get('low_rated') == '1'
    no_vol_req  = request.GET.get('no_vol_req') == '1'
    skills_q    = request.GET.get('skills', '').strip()
    sort        = request.GET.get('sort', '-date_joined')

    if role:
        qs = qs.filter(role=role)
    if active == '1':
        qs = qs.filter(is_active=True)
    elif active == '0':
        qs = qs.filter(is_active=False)
    if verified == '1':
        qs = qs.filter(is_verified=True)
    elif verified == '0':
        qs = qs.filter(is_verified=False)
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if joined_from:
        qs = qs.filter(date_joined__date__gte=joined_from)
    if joined_to:
        qs = qs.filter(date_joined__date__lte=joined_to)
    if tier:
        if tier == 'none':
            qs = qs.filter(volunteer_profile__points__lt=50)
        elif tier == 'bronze':
            qs = qs.filter(volunteer_profile__points__gte=50,
                           volunteer_profile__points__lt=100)
        elif tier == 'silver':
            qs = qs.filter(volunteer_profile__points__gte=100,
                           volunteer_profile__points__lt=200)
        elif tier == 'gold':
            qs = qs.filter(volunteer_profile__points__gte=200)
    if low_rated:
        cutoff_lr = timezone.now() - timedelta(days=LOW_RATING_RECENT_DAYS)
        low_ids = (
            Review.objects
            .filter(rating__lte=LOW_RATING_THRESHOLD, created_at__gte=cutoff_lr)
            .values_list('reviewee_id', flat=True).distinct()
        )
        qs = qs.filter(pk__in=low_ids)
    if no_vol_req:
        ids_with_open_unassigned = (
            Request.objects
            .filter(status='open', volunteer__isnull=True, is_archived=False)
            .values_list('user_id', flat=True).distinct()
        )
        qs = qs.filter(pk__in=ids_with_open_unassigned, role='user')
    if skills_q:
        qs = qs.filter(volunteer_profile__skills__icontains=skills_q)

    allowed_sorts = {
        'date_joined', '-date_joined',
        'username', '-username',
    }
    if sort not in allowed_sorts:
        sort = '-date_joined'
    qs = qs.order_by(sort)

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj  = paginator.get_page(request.GET.get('page', 1))
    qs_pg     = _qs_no_page(request.GET)   # query string without 'page'

    has_filters = bool(
        role or q or joined_from or joined_to or tier or skills_q
        or active != '' or verified != ''
        or low_rated or no_vol_req
    )

    context = {
        'page_obj':    page_obj,
        'total_count': paginator.count,
        'qs_pg':       qs_pg,
        'has_filters': has_filters,
        # preserved filter values
        'f_role':        role,
        'f_active':      active,
        'f_verified':    verified,
        'f_q':           q,
        'f_joined_from': joined_from,
        'f_joined_to':   joined_to,
        'f_tier':        tier,
        'f_low_rated':   low_rated,
        'f_no_vol_req':  no_vol_req,
        'f_skills':      skills_q,
        'f_sort':        sort,
    }
    return render(request, 'dashboard/users.html', context)


@staff_member_required
def manage_requests(request):
    # ── POST: archive / restore ────────────────────────────────────────────
    if request.method == 'POST':
        req_id    = request.POST.get('request_id')
        action    = request.POST.get('action')
        return_to = request.POST.get('return_to', '/dashboard/requests/')
        reason    = request.POST.get('reason', '').strip()
        req_obj   = get_object_or_404(Request, pk=req_id)

        if action == 'archive':
            if not reason:
                messages.error(request, "A reason is required to archive a request.")
            else:
                req_obj.is_archived   = True
                req_obj.archived_at   = timezone.now()
                req_obj.archive_reason = reason
                req_obj.save(update_fields=['is_archived', 'archived_at', 'archive_reason'])
                _log(request, 'archive_request', 'Request', req_obj, reason=reason)
                messages.success(request,
                    f'Request \u201c{req_obj.title}\u201d archived.')
        elif action == 'restore':
            req_obj.is_archived    = False
            req_obj.archived_at    = None
            req_obj.archive_reason = ''
            req_obj.save(update_fields=['is_archived', 'archived_at', 'archive_reason'])
            _log(request, 'restore_request', 'Request', req_obj, reason=reason)
            messages.success(request,
                f'Request \u201c{req_obj.title}\u201d restored to active.')
        return redirect(return_to)

    # ── GET: build filtered queryset ───────────────────────────────────────
    qs = Request.objects.select_related('user', 'volunteer', 'category').all()

    show_archived = request.GET.get('archived') == '1'
    qs = qs.filter(is_archived=show_archived)

    q           = request.GET.get('q', '').strip()
    status      = request.GET.get('status', '')
    priority    = request.GET.get('priority', '')
    category_id = request.GET.get('category', '')
    requester   = request.GET.get('requester', '').strip()
    volunteer_q = request.GET.get('volunteer', '').strip()
    skills_q    = request.GET.get('skills', '').strip()
    date_from   = request.GET.get('date_from', '')
    date_to     = request.GET.get('date_to', '')
    unassigned  = request.GET.get('unassigned') == '1'
    stale       = request.GET.get('stale') == '1'
    sort        = request.GET.get('sort', '-created_at')

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if requester:
        qs = qs.filter(user__username__icontains=requester)
    if volunteer_q:
        qs = qs.filter(volunteer__username__icontains=volunteer_q)
    if skills_q:
        qs = qs.filter(required_skills__icontains=skills_q)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if stale:
        cutoff_st = timezone.now() - timedelta(days=UNASSIGNED_DAYS_THRESHOLD)
        qs = qs.filter(volunteer__isnull=True, status='open', created_at__lte=cutoff_st)
    elif unassigned:
        qs = qs.filter(volunteer__isnull=True)

    allowed_sorts = {
        'created_at', '-created_at',
        'title', '-title',
        'priority', '-priority',
        'status', '-status',
    }
    if sort not in allowed_sorts:
        sort = '-created_at'
    qs = qs.order_by(sort)

    paginator  = Paginator(qs, PAGE_SIZE)
    page_obj   = paginator.get_page(request.GET.get('page', 1))
    qs_pg      = _qs_no_page(request.GET)
    categories = Category.objects.all()

    # Date string for "Cancelled this week" quick chip
    week_ago = (timezone.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    has_filters = bool(
        q or status or priority or category_id
        or requester or volunteer_q or skills_q
        or date_from or date_to
        or unassigned or stale or show_archived
    )

    context = {
        'page_obj':       page_obj,
        'total_count':    paginator.count,
        'qs_pg':          qs_pg,
        'categories':     categories,
        'week_ago':       week_ago,
        'has_filters':    has_filters,
        'unassigned_days': UNASSIGNED_DAYS_THRESHOLD,
        # preserved filter values
        'f_q':          q,
        'f_status':     status,
        'f_priority':   priority,
        'f_category':   category_id,
        'f_requester':  requester,
        'f_volunteer':  volunteer_q,
        'f_skills':     skills_q,
        'f_date_from':  date_from,
        'f_date_to':    date_to,
        'f_unassigned': unassigned,
        'f_stale':      stale,
        'f_archived':   show_archived,
        'f_sort':       sort,
    }
    return render(request, 'dashboard/requests.html', context)


@staff_member_required
def manage_badges(request):
    from rewards.models import Badge, UserBadge
    badges = Badge.objects.all()
    volunteers = CustomUser.objects.filter(role='volunteer')
    user_badges = UserBadge.objects.all().order_by('-awarded_at')

    if request.method == 'POST' and 'create_badge' in request.POST:
        name = request.POST.get('name')
        icon = request.POST.get('icon')
        desc = request.POST.get('description')
        if name and icon:
            badge = Badge.objects.create(name=name, icon=icon, description=desc)
            _log(request, 'create_badge', 'Badge', badge)
            messages.success(request, "Badge created successfully.")

    return render(request, 'dashboard/badges.html', {
        'badges': badges,
        'volunteers': volunteers,
        'user_badges': user_badges,
    })


@staff_member_required
def award_badge(request):
    from rewards.models import Badge, UserBadge
    from notifications.models import Notification
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        badge_id = request.POST.get('badge_id')
        if user_id and badge_id:
            user = get_object_or_404(CustomUser, pk=user_id)
            badge = get_object_or_404(Badge, pk=badge_id)
            UserBadge.objects.get_or_create(user=user, badge=badge)
            Notification.objects.create(
                user=user,
                message=f'🏅 You have been awarded the {badge.name} badge by an admin!',
            )
            _log(request, 'award_badge', 'Badge', badge,
                 reason=f'Awarded to {user.username}')
            messages.success(request, f"Badge {badge.name} awarded to {user.username}.")
    return redirect('dashboard:manage_badges')


# ── Phase 3: Reports & Complaints Views ───────────────────────────────────────

from django.contrib.auth.decorators import login_required
from .forms import ReportSubmissionForm
from notifications.models import Notification


@login_required
def submit_report(request):
    """
    User-facing endpoint to submit a report/complaint.
    Rate-limited to 5 reports per user per hour.
    """
    request_id = request.GET.get('request_id') or request.POST.get('request_id')
    reported_user_id = request.GET.get('user_id') or request.POST.get('user_id')
    report_type = request.GET.get('type') or request.POST.get('type', '')

    related_req = None
    if request_id:
        related_req = Request.objects.filter(pk=request_id).first()

    reported_user = None
    if reported_user_id:
        reported_user = CustomUser.objects.filter(pk=reported_user_id).first()
    elif related_req:
        # Auto-attach other party
        if request.user == related_req.user:
            reported_user = related_req.volunteer
        elif request.user == related_req.volunteer:
            reported_user = related_req.user

    if not report_type:
        if reported_user:
            if reported_user.role == 'volunteer':
                report_type = 'report_volunteer'
            else:
                report_type = 'report_user'
        else:
            report_type = 'general_complaint'

    if request.method == 'POST':
        # Rate-limiting: max 5 submissions in the last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_count = Report.objects.filter(reporter=request.user, created_at__gte=one_hour_ago).count()
        if recent_count >= 5:
            messages.error(request, "You have reached the submission limit for reports this hour. Please try again later.")
            return render(request, 'dashboard/submit_report.html', {
                'form': ReportSubmissionForm(),
                'related_req': related_req,
                'reported_user': reported_user,
                'report_type': report_type,
            })

        form = ReportSubmissionForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = reported_user
            report.related_request = related_req
            report.report_type = report_type
            report.save()

            # If high severity, notify staff in-app
            if report.severity == 'high':
                staff_users = CustomUser.objects.filter(is_staff=True)
                for staff in staff_users:
                    Notification.objects.create(
                        user=staff,
                        message=f"🚨 High-severity report submitted ({report.reference_number}): {report.get_category_display()}"
                    )

            return render(request, 'dashboard/report_confirmation.html', {
                'report': report,
            })
    else:
        form = ReportSubmissionForm()

    return render(request, 'dashboard/submit_report.html', {
        'form': form,
        'related_req': related_req,
        'reported_user': reported_user,
        'report_type': report_type,
    })


@staff_member_required
def manage_reports(request):
    """Admin Reports Inbox with filtering, sorting, and pagination."""
    qs = Report.objects.select_related('reporter', 'reported_user', 'related_request', 'assigned_staff').all()

    q = request.GET.get('q', '').strip()
    report_type = request.GET.get('type', '')
    category = request.GET.get('category', '')
    severity = request.GET.get('severity', '')
    status = request.GET.get('status', '')
    assigned_staff_id = request.GET.get('assigned_staff', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    reporter_q = request.GET.get('reporter', '').strip()
    reported_q = request.GET.get('reported', '').strip()
    sort = request.GET.get('sort', '-created_at')

    if q:
        qs = qs.filter(
            Q(reference_number__icontains=q) |
            Q(description__icontains=q) |
            Q(reporter__username__icontains=q) |
            Q(reported_user__username__icontains=q)
        )
    if report_type:
        qs = qs.filter(report_type=report_type)
    if category:
        qs = qs.filter(category=category)
    if severity:
        qs = qs.filter(severity=severity)
    if status:
        qs = qs.filter(status=status)
    if assigned_staff_id:
        qs = qs.filter(assigned_staff_id=assigned_staff_id)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if reporter_q:
        qs = qs.filter(reporter__username__icontains=reporter_q)
    if reported_q:
        qs = qs.filter(reported_user__username__icontains=reported_q)

    allowed_sorts = {
        'created_at', '-created_at',
        'severity', '-severity',
        'status', '-status',
        'reference_number', '-reference_number',
    }
    if sort not in allowed_sorts:
        sort = '-created_at'
    qs = qs.order_by(sort)

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    qs_pg = _qs_no_page(request.GET)

    staff_members = CustomUser.objects.filter(is_staff=True).order_by('username')

    has_filters = bool(
        q or report_type or category or severity or status or
        assigned_staff_id or date_from or date_to or reporter_q or reported_q
    )

    context = {
        'page_obj': page_obj,
        'total_count': paginator.count,
        'qs_pg': qs_pg,
        'has_filters': has_filters,
        'staff_members': staff_members,
        'type_choices': Report.TYPE_CHOICES,
        'category_choices': Report.CATEGORY_CHOICES,
        'severity_choices': Report.SEVERITY_CHOICES,
        'status_choices': Report.STATUS_CHOICES,
        # Preserved filter values
        'f_q': q,
        'f_type': report_type,
        'f_category': category,
        'f_severity': severity,
        'f_status': status,
        'f_staff': assigned_staff_id,
        'f_date_from': date_from,
        'f_date_to': date_to,
        'f_reporter': reporter_q,
        'f_reported': reported_q,
        'f_sort': sort,
    }
    return render(request, 'dashboard/reports.html', context)


@staff_member_required
def report_detail(request, pk):
    """
    Detailed report review page with context, notes, status transitions,
    and moderation actions.
    """
    report = get_object_or_404(
        Report.objects.select_related('reporter', 'reported_user', 'related_request', 'assigned_staff'),
        pk=pk
    )

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        # 1. Add internal note
        if action_type == 'add_note':
            note_text = request.POST.get('note', '').strip()
            if note_text:
                ReportNote.objects.create(
                    report=report,
                    staff=request.user,
                    note=note_text
                )
                messages.success(request, "Internal note added.")
            return redirect('dashboard:report_detail', pk=pk)

        # 2. Update status / assignment
        elif action_type == 'update_status':
            new_status = request.POST.get('status')
            new_assigned_id = request.POST.get('assigned_staff')
            status_reason = request.POST.get('status_reason', '').strip()

            status_changed = False
            if new_status and new_status in dict(Report.STATUS_CHOICES):
                if report.status != new_status:
                    old_status = report.status
                    report.status = new_status
                    if new_status in ['resolved', 'action_taken', 'dismissed']:
                        report.resolved_at = timezone.now()
                    report.save(update_fields=['status', 'resolved_at'])
                    ReportStatusHistory.objects.create(
                        report=report,
                        changed_by=request.user,
                        old_status=old_status,
                        new_status=new_status,
                        reason=status_reason
                    )
                    _log(request, 'update_report_status', 'Report', report,
                         reason=f"Status: {old_status} -> {new_status}. {status_reason}")
                    status_changed = True

            if new_assigned_id != '':
                assigned_user = CustomUser.objects.filter(pk=new_assigned_id, is_staff=True).first() if new_assigned_id else None
                if report.assigned_staff != assigned_user:
                    report.assigned_staff = assigned_user
                    report.save(update_fields=['assigned_staff'])
                    _log(request, 'assign_report', 'Report', report,
                         reason=f"Assigned to {assigned_user.username if assigned_user else 'None'}")
                    messages.success(request, "Staff assignment updated.")

            if status_changed:
                messages.success(request, f"Status updated to {report.get_status_display()}.")
            return redirect('dashboard:report_detail', pk=pk)

        # 3. Reply to reporter
        elif action_type == 'reply_reporter':
            reply_message = request.POST.get('reply_message', '').strip()
            if reply_message:
                Notification.objects.create(
                    user=report.reporter,
                    message=f"Update regarding report {report.reference_number}: {reply_message}"
                )
                ReportNote.objects.create(
                    report=report,
                    staff=request.user,
                    note=f"[Reply sent to reporter]: {reply_message}"
                )
                _log(request, 'reply_report_reporter', 'Report', report, reason=reply_message)
                messages.success(request, "Message sent to reporter as an in-app notification.")
            return redirect('dashboard:report_detail', pk=pk)

        # 4. Moderation actions on reported user
        elif action_type == 'moderation_action':
            action = request.POST.get('action')  # warn, suspend, remove_verification, dismiss
            reason = request.POST.get('reason', '').strip()

            if not reason:
                messages.error(request, "A reason is mandatory for any moderation action.")
                return redirect('dashboard:report_detail', pk=pk)

            reported = report.reported_user
            if action == 'dismiss':
                old_status = report.status
                report.status = 'dismissed'
                report.resolved_at = timezone.now()
                report.save(update_fields=['status', 'resolved_at'])
                ReportStatusHistory.objects.create(
                    report=report,
                    changed_by=request.user,
                    old_status=old_status,
                    new_status='dismissed',
                    reason=reason
                )
                _log(request, 'dismiss_report', 'Report', report, reason=reason)
                messages.success(request, "Report dismissed.")

            elif action == 'warn' and reported:
                Notification.objects.create(
                    user=reported,
                    message=f"Notice from Moderation: Please adhere to Companio community standards. Reason: {reason}"
                )
                report.status = 'action_taken'
                report.resolved_at = timezone.now()
                report.save(update_fields=['status', 'resolved_at'])
                _log(request, 'warn_user', 'User', reported, reason=f"Report {report.reference_number}: {reason}")
                messages.success(request, f"Warning notification sent to {reported.username}.")

            elif action == 'remove_verification' and reported:
                reported.is_verified = False
                reported.save(update_fields=['is_verified'])
                Notification.objects.create(
                    user=reported,
                    message="Your volunteer verification badge has been revoked due to a moderation review."
                )
                report.status = 'action_taken'
                report.resolved_at = timezone.now()
                report.save(update_fields=['status', 'resolved_at'])
                _log(request, 'remove_verification', 'User', reported, reason=f"Report {report.reference_number}: {reason}")
                messages.success(request, f"Verification revoked for {reported.username}.")

            elif action == 'suspend' and reported:
                reported.is_active = False
                reported.save(update_fields=['is_active'])

                # If suspended volunteer: re-open assigned requests and notify users
                if reported.role == 'volunteer':
                    active_assigned = Request.objects.filter(volunteer=reported, status='assigned')
                    for req in active_assigned:
                        is_hp = req.priority == 'High'
                        req.status = 'open'
                        req.volunteer = None
                        req.save(update_fields=['status', 'volunteer'])

                        # Notify requester
                        Notification.objects.create(
                            user=req.user,
                            message=f"Your request '{req.title}' has been returned to Open status because the assigned volunteer is currently unavailable."
                        )

                        # If high priority, alert staff
                        if is_hp:
                            for staff in CustomUser.objects.filter(is_staff=True):
                                Notification.objects.create(
                                    user=staff,
                                    message=f"⚠️ High-priority request #{req.pk} returned to Open following volunteer suspension."
                                )

                Notification.objects.create(
                    user=reported,
                    message=f"Your account has been suspended pending review. Reason: {reason}"
                )
                report.status = 'action_taken'
                report.resolved_at = timezone.now()
                report.save(update_fields=['status', 'resolved_at'])
                _log(request, 'suspend_user', 'User', reported, reason=f"Report {report.reference_number}: {reason}")
                messages.success(request, f"Account {reported.username} has been suspended. Assigned requests returned to Open.")

            return redirect('dashboard:report_detail', pk=pk)

    notes = report.notes.select_related('staff').all()
    history = report.status_history.select_related('changed_by').all()
    staff_members = CustomUser.objects.filter(is_staff=True).order_by('username')

    context = {
        'report': report,
        'notes': notes,
        'history': history,
        'staff_members': staff_members,
        'status_choices': Report.STATUS_CHOICES,
    }
    return render(request, 'dashboard/report_detail.html', context)


# ── Phase 4: User / Volunteer Profile Views & Review Moderation ───────────────

from django.db.models import Avg, Count
from rewards.models import Certificate, UserBadge


@staff_member_required
def user_detail(request, pk):
    """
    Comprehensive admin detail view for both Volunteers and Regular Users.
    Combines profile, stats, ratings, certificates, badges, cancellation counts,
    reports received & filed, and review moderation.
    Flags volunteers crossing default threshold of 3 reports in 90 days.
    """
    user_obj = get_object_or_404(
        CustomUser.objects.select_related('volunteer_profile'),
        pk=pk
    )

    is_volunteer = user_obj.role == 'volunteer'

    # Reports context
    reports_received = Report.objects.filter(reported_user=user_obj).order_by('-created_at')
    reports_filed = Report.objects.filter(reporter=user_obj).order_by('-created_at')

    # Volunteer threshold calculation: 3 reports in last 90 days
    ninety_days_ago = timezone.now() - timedelta(days=90)
    reports_90d_count = reports_received.filter(created_at__gte=ninety_days_ago).count()
    is_flagged_for_reports = (reports_90d_count >= 3)

    # Reviews received & average rating
    reviews_received = Review.objects.filter(reviewee=user_obj).select_related('reviewer', 'request').order_by('-created_at')
    avg_rating_val = reviews_received.aggregate(Avg('rating'))['rating__avg']
    avg_rating = round(avg_rating_val, 1) if avg_rating_val is not None else None
    low_rating_count = reviews_received.filter(rating__lte=LOW_RATING_THRESHOLD).count()

    if is_volunteer:
        # Completed requests & cancellations/withdrawals
        completed_requests = Request.objects.filter(volunteer=user_obj, status='completed').count()
        cancelled_requests = Request.objects.filter(volunteer=user_obj, status='cancelled').count()
        recent_requests = Request.objects.filter(volunteer=user_obj).select_related('user', 'category').order_by('-created_at')[:10]

        # Points tier
        profile = getattr(user_obj, 'volunteer_profile', None)
        points = profile.points if profile else 0
        if points >= 200:
            tier = 'Gold'
        elif points >= 100:
            tier = 'Silver'
        elif points >= 50:
            tier = 'Bronze'
        else:
            tier = 'Below Bronze'

        # Badges and certificates
        badges = UserBadge.objects.filter(user=user_obj).select_related('badge')
        certificates = Certificate.objects.filter(user=user_obj).order_by('-issue_date')

        context = {
            'user_obj': user_obj,
            'is_volunteer': True,
            'profile': profile,
            'tier': tier,
            'points': points,
            'avg_rating': avg_rating,
            'reviews_received': reviews_received,
            'low_rating_count': low_rating_count,
            'completed_count': completed_requests,
            'cancelled_count': cancelled_requests,
            'recent_requests': recent_requests,
            'reports_received': reports_received,
            'reports_filed': reports_filed,
            'reports_90d_count': reports_90d_count,
            'is_flagged_for_reports': is_flagged_for_reports,
            'badges': badges,
            'certificates': certificates,
        }
    else:
        # Regular user view
        user_requests = Request.objects.filter(user=user_obj).select_related('volunteer', 'category').order_by('-created_at')
        open_count = user_requests.filter(status='open').count()
        completed_count = user_requests.filter(status='completed').count()
        cancelled_count = user_requests.filter(status='cancelled').count()

        context = {
            'user_obj': user_obj,
            'is_volunteer': False,
            'user_requests': user_requests,
            'open_count': open_count,
            'completed_count': completed_count,
            'cancelled_count': cancelled_count,
            'reports_received': reports_received,
            'reports_filed': reports_filed,
            'reviews_received': reviews_received,
            'avg_rating': avg_rating,
        }

    return render(request, 'dashboard/user_detail.html', context)


@staff_member_required
def toggle_review_hidden(request, review_id):
    """
    Moderator action to flag or hide abusive/inappropriate review text.
    Recorded in the AdminAuditLog.
    """
    review = get_object_or_404(Review, pk=review_id)
    return_to = request.POST.get('return_to', f"/dashboard/users/{review.reviewee.pk}/")
    reason = request.POST.get('reason', '').strip()

    if request.method == 'POST':
        action = request.POST.get('action')  # 'hide', 'unhide', 'flag'

        if action == 'hide':
            if not reason:
                messages.error(request, "A reason is required to hide a review comment.")
                return redirect(return_to)
            review.is_hidden = True
            review.hidden_reason = reason
            review.hidden_at = timezone.now()
            review.save(update_fields=['is_hidden', 'hidden_reason', 'hidden_at'])
            _log(request, 'hide_review_text', 'Review', review, reason=reason)
            messages.success(request, "Review text hidden from public view.")

        elif action == 'unhide':
            review.is_hidden = False
            review.hidden_reason = ''
            review.hidden_at = None
            review.save(update_fields=['is_hidden', 'hidden_reason', 'hidden_at'])
            _log(request, 'unhide_review_text', 'Review', review, reason=reason or 'Restored by staff')
            messages.success(request, "Review text restored.")

        elif action == 'flag':
            review.is_flagged = not review.is_flagged
            review.save(update_fields=['is_flagged'])
            status_text = "flagged for moderation" if review.is_flagged else "unflagged"
            _log(request, 'flag_review', 'Review', review, reason=reason)
            messages.success(request, f"Review {status_text}.")

    return redirect(return_to)


# ── Phase 5: Request-Scoped Message Viewing & Access Logging ─────────────────

from messaging.models import Message


@staff_member_required
def request_messages(request, request_id):
    """
    Staff-only threaded message view strictly scoped to a specific request.
    Admins can only reach this from a request or a report.
    If not accessed via a tied report, a reason is required and verified before viewing.
    Every access is logged to AdminAuditLog.
    Supports filtering by keyword, date range, and sender.
    """
    assist_req = get_object_or_404(Request.objects.select_related('user', 'volunteer'), pk=request_id)

    report_id = request.GET.get('report_id') or request.POST.get('report_id')
    tied_report = None
    if report_id:
        tied_report = Report.objects.filter(pk=report_id, related_request=assist_req).first()

    session_access_key = f"msg_access_req_{assist_req.pk}"
    has_permission = (tied_report is not None) or request.session.get(session_access_key)

    # If POSTing a reason to unlock access
    if request.method == 'POST' and 'access_reason' in request.POST:
        reason = request.POST.get('access_reason', '').strip()
        if len(reason) < 5:
            messages.error(request, "A clear, valid justification (min 5 characters) is required to access user messages.")
            return render(request, 'dashboard/request_messages_reason.html', {
                'assist_req': assist_req,
                'report_id': report_id,
            })

        # Record access in AdminAuditLog
        _log(request, 'view_request_messages', 'Request', assist_req,
             reason=f"Message log access reason: {reason}")

        request.session[session_access_key] = True
        return redirect(f"{request.path}?{request.GET.urlencode()}")

    # If not authorized yet and not tied to report, show reason gating form
    if not has_permission:
        return render(request, 'dashboard/request_messages_reason.html', {
            'assist_req': assist_req,
            'report_id': report_id,
        })

    # If accessed with a report directly for the first time, log the access
    if tied_report and not request.session.get(session_access_key):
        _log(request, 'view_request_messages', 'Request', assist_req,
             reason=f"Accessed via Report #{tied_report.reference_number}")
        request.session[session_access_key] = True

    # Filter messages
    messages_qs = Message.objects.filter(request=assist_req).select_related('sender', 'receiver').order_by('timestamp')

    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sender_id = request.GET.get('sender', '')

    if q:
        messages_qs = messages_qs.filter(content__icontains=q)
    if date_from:
        messages_qs = messages_qs.filter(timestamp__date__gte=date_from)
    if date_to:
        messages_qs = messages_qs.filter(timestamp__date__lte=date_to)
    if sender_id:
        messages_qs = messages_qs.filter(sender_id=sender_id)

    has_filters = bool(q or date_from or date_to or sender_id)

    context = {
        'assist_req': assist_req,
        'tied_report': tied_report,
        'messages_list': messages_qs,
        'total_messages_count': messages_qs.count(),
        'has_filters': has_filters,
        # Preserved filter values
        'f_q': q,
        'f_date_from': date_from,
        'f_date_to': date_to,
        'f_sender': sender_id,
    }
    return render(request, 'dashboard/request_messages.html', context)


@staff_member_required
def audit_logs(request):
    """
    Searchable, filterable audit log viewer for administrators.
    Displays who did what, target, timestamp, and reason.
    """
    qs = AdminAuditLog.objects.select_related('staff').all()

    action_q = request.GET.get('action', '')
    target_type = request.GET.get('target_type', '')
    staff_q = request.GET.get('staff', '')
    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if action_q:
        qs = qs.filter(action=action_q)
    if target_type:
        qs = qs.filter(target_type=target_type)
    if staff_q:
        qs = qs.filter(staff_id=staff_q)
    if q:
        qs = qs.filter(
            Q(target_repr__icontains=q) |
            Q(reason__icontains=q) |
            Q(target_id__icontains=q)
        )
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    qs_pg = _qs_no_page(request.GET)

    staff_members = CustomUser.objects.filter(is_staff=True).order_by('username')
    action_types = AdminAuditLog.objects.values_list('action', flat=True).distinct()
    target_types = AdminAuditLog.objects.values_list('target_type', flat=True).distinct()

    has_filters = bool(action_q or target_type or staff_q or q or date_from or date_to)

    context = {
        'page_obj': page_obj,
        'total_count': paginator.count,
        'qs_pg': qs_pg,
        'has_filters': has_filters,
        'staff_members': staff_members,
        'action_types': sorted(filter(None, action_types)),
        'target_types': sorted(filter(None, target_types)),
        'f_action': action_q,
        'f_target_type': target_type,
        'f_staff': staff_q,
        'f_q': q,
        'f_date_from': date_from,
        'f_date_to': date_to,
    }
    return render(request, 'dashboard/audit_logs.html', context)


# ── Phase 6: Verification Queue & Administrative Actions ───────────────────────

@staff_member_required
def verification_queue(request):
    """
    Displays the queue of unverified volunteers with their skills, profile details,
    and verification history. Staff can approve or reject verification from here.
    """
    unverified_volunteers = CustomUser.objects.filter(
        role='volunteer',
        is_verified=False
    ).select_related('volunteer_profile').order_by('-date_joined')

    # Recently verified volunteers for audit context
    recently_verified = CustomUser.objects.filter(
        role='volunteer',
        is_verified=True,
        verified_by__isnull=False
    ).select_related('volunteer_profile', 'verified_by').order_by('-verified_at')[:10]

    context = {
        'unverified_volunteers': unverified_volunteers,
        'recently_verified': recently_verified,
        'total_pending': unverified_volunteers.count(),
    }
    return render(request, 'dashboard/verification_queue.html', context)


@staff_member_required
def verification_action(request, user_id):
    """
    Approve or reject a volunteer's verification status.
    Mandatory reason/notes recorded and logged in AdminAuditLog.
    """
    if request.method != 'POST':
        return redirect('dashboard:verification_queue')

    volunteer = get_object_or_404(CustomUser, pk=user_id, role='volunteer')
    action = request.POST.get('action')  # 'approve' or 'reject'
    notes = request.POST.get('notes', '').strip()
    return_to = request.POST.get('return_to', '/dashboard/verification/')

    if not notes:
        messages.error(request, "Please provide verification notes or a reason.")
        return redirect(return_to)

    if action == 'approve':
        volunteer.is_verified = True
        volunteer.verified_by = request.user
        volunteer.verified_at = timezone.now()
        volunteer.verification_notes = notes
        volunteer.save()

        _log(request, 'approve_verification', 'Volunteer', volunteer, reason=notes)
        messages.success(request, f"Volunteer @{volunteer.username} has been verified successfully.")
    elif action == 'reject':
        volunteer.is_verified = False
        volunteer.verification_notes = f"Rejected by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}: {notes}"
        volunteer.save()

        _log(request, 'reject_verification', 'Volunteer', volunteer, reason=notes)
        messages.warning(request, f"Verification for @{volunteer.username} was rejected.")
    else:
        messages.error(request, "Unknown verification action.")

    return redirect(return_to)


@staff_member_required
def adjust_points(request, user_id):
    """
    Admin points adjustment with a required reason, logged into AdminAuditLog.
    """
    if request.method != 'POST':
        return redirect('dashboard:user_detail', pk=user_id)

    volunteer = get_object_or_404(CustomUser, pk=user_id, role='volunteer')
    profile = getattr(volunteer, 'volunteer_profile', None)
    if not profile:
        messages.error(request, "Volunteer profile not found.")
        return redirect('dashboard:user_detail', pk=user_id)

    delta_str = request.POST.get('points_delta', '').strip()
    reason = request.POST.get('reason', '').strip()

    if not reason:
        messages.error(request, "A reason is strictly required when adjusting volunteer points.")
        return redirect('dashboard:user_detail', pk=user_id)

    try:
        points_delta = int(delta_str)
    except ValueError:
        messages.error(request, "Invalid points amount.")
        return redirect('dashboard:user_detail', pk=user_id)

    old_points = profile.points
    profile.points = max(0, profile.points + points_delta)
    profile.save()

    log_reason = f"Points adjusted by {points_delta:+d} (from {old_points} to {profile.points}). Reason: {reason}"
    _log(request, 'adjust_points', 'Volunteer', volunteer, reason=log_reason)

    messages.success(request, f"Points for @{volunteer.username} adjusted to {profile.points} ({points_delta:+d}).")
    return redirect('dashboard:user_detail', pk=user_id)


@staff_member_required
def revoke_badge(request, user_badge_id):
    """
    Revoke an awarded badge from a user, requiring a logged reason.
    """
    if request.method != 'POST':
        return redirect('dashboard:manage_users')

    user_badge = get_object_or_404(UserBadge, pk=user_badge_id)
    target_user = user_badge.user
    badge_name = user_badge.badge.name
    reason = request.POST.get('reason', '').strip()
    return_to = request.POST.get('return_to', f'/dashboard/users/{target_user.pk}/')

    if not reason:
        messages.error(request, "A reason is required to revoke a badge.")
        return redirect(return_to)

    log_reason = f"Revoked badge '{badge_name}'. Reason: {reason}"
    _log(request, 'revoke_badge', 'UserBadge', user_badge, reason=log_reason)

    user_badge.delete()
    messages.warning(request, f"Badge '{badge_name}' revoked from @{target_user.username}.")
    return redirect(return_to)


@staff_member_required
def revoke_certificate(request, cert_id):
    """
    Revoke a certificate from a user, requiring a logged reason.
    """
    if request.method != 'POST':
        return redirect('dashboard:manage_users')

    cert = get_object_or_404(Certificate, pk=cert_id)
    target_user = cert.user
    cert_title = cert.title
    reason = request.POST.get('reason', '').strip()
    return_to = request.POST.get('return_to', f'/dashboard/users/{target_user.pk}/')

    if not reason:
        messages.error(request, "A reason is required to revoke a certificate.")
        return redirect(return_to)

    log_reason = f"Revoked certificate '{cert_title}'. Reason: {reason}"
    _log(request, 'revoke_certificate', 'Certificate', cert, reason=log_reason)

    cert.delete()
    messages.warning(request, f"Certificate '{cert_title}' revoked from @{target_user.username}.")
    return redirect(return_to)




