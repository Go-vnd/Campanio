from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Request, Category
from .forms import RequestForm
from notifications.models import Notification


def _create_notification(user, message_text):
    """Helper to create a notification for a user."""
    Notification.objects.create(user=user, message=message_text)


def request_list(request):
    categories = Category.objects.all()
    category_filter = request.GET.get('category', '')
    search_q = request.GET.get('q', '')
    location_filter = request.GET.get('location', '')
    near_me = request.GET.get('near_me') == '1'

    if request.user.is_authenticated and request.user.role == 'volunteer':
        reqs = Request.objects.filter(status='open', is_archived=False).order_by('-created_at')
        # Apply category and keyword filters
        if category_filter:
            reqs = reqs.filter(category__id=category_filter)
        if search_q:
            reqs = reqs.filter(title__icontains=search_q)
        if location_filter:
            reqs = reqs.filter(location__icontains=location_filter)

        profile = getattr(request.user, 'volunteer_profile', None)
        try:
            vol_skills = [
                s.strip().lower()
                for s in profile.skills.split(',')
                if s.strip()
            ] if profile and profile.skills else []
        except Exception:
            vol_skills = []

        vol_location = (profile.location.strip().lower() if profile and profile.location else '')
        vol_loc_tokens = [t.strip() for t in vol_location.replace(',', ' ').split() if len(t.strip()) > 2]

        if near_me and vol_loc_tokens:
            loc_q = Q()
            for token in vol_loc_tokens:
                loc_q |= Q(location__icontains=token)
            reqs = reqs.filter(loc_q)

        # Multi-factor matching score calculation:
        # 1. Location match: exact or token match in request location
        # 2. Skill match: shared skills
        # Requests with both Skill + Location match come first, followed by single matches
        both_matched = []
        loc_matched = []
        skill_matched = []
        unmatched = []

        for req in reqs:
            req_skills = [s.strip().lower() for s in req.required_skills.split(',') if s.strip()]
            has_skill_match = bool(vol_skills and any(s in vol_skills for s in req_skills))

            req_loc = (req.location or '').strip().lower()
            has_loc_match = False
            if vol_location and req_loc:
                if vol_location in req_loc or req_loc in vol_location:
                    has_loc_match = True
                elif any(tok in req_loc for tok in vol_loc_tokens):
                    has_loc_match = True

            req.is_skill_match = has_skill_match
            req.is_location_match = has_loc_match

            if has_skill_match and has_loc_match:
                both_matched.append(req)
            elif has_loc_match:
                loc_matched.append(req)
            elif has_skill_match:
                skill_matched.append(req)
            else:
                unmatched.append(req)

        sorted_requests = both_matched + loc_matched + skill_matched + unmatched
        all_matched_ids = [r.pk for r in (both_matched + loc_matched + skill_matched)]

        context = {
            'requests': sorted_requests,
            'matched_ids': all_matched_ids,
            'both_matched_count': len(both_matched),
            'loc_matched_count': len(loc_matched),
            'skill_matched_count': len(skill_matched),
            'vol_location': profile.location if profile else '',
            'near_me': near_me,
            'view_mode': 'volunteer',
            'categories': categories,
            'category_filter': category_filter,
            'search_q': search_q,
            'location_filter': location_filter,
        }

    elif request.user.is_authenticated and request.user.role == 'admin':
        reqs = Request.objects.filter(is_archived=False).order_by('-created_at')
        if category_filter:
            reqs = reqs.filter(category__id=category_filter)
        if search_q:
            reqs = reqs.filter(title__icontains=search_q)
        context = {
            'requests': reqs,
            'view_mode': 'admin',
            'categories': categories,
            'category_filter': category_filter,
            'search_q': search_q,
        }

    elif request.user.is_authenticated:
        reqs = Request.objects.filter(user=request.user, is_archived=False).order_by('-created_at')
        if category_filter:
            reqs = reqs.filter(category__id=category_filter)
        if search_q:
            reqs = reqs.filter(title__icontains=search_q)
        context = {
            'requests': reqs,
            'view_mode': 'user',
            'categories': categories,
            'category_filter': category_filter,
            'search_q': search_q,
        }
    else:
        reqs = Request.objects.filter(status='open', is_archived=False).order_by('-created_at')[:12]
        context = {'requests': reqs, 'view_mode': 'public'}

    return render(request, 'assist_requests/request_list.html', context)


@login_required
def request_create(request):
    if request.user.role in ['volunteer', 'admin']:
        messages.error(request, f'{request.user.role.title()}s cannot create assistance requests.')
        return redirect('assist_requests:request_list')

    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.user = request.user
            req.save()
            messages.success(request, 'Assistance request created successfully!')
            return redirect('assist_requests:request_list')
    else:
        form = RequestForm()

    return render(request, 'assist_requests/request_form.html', {'form': form})


@login_required
def request_detail(request, pk):
    req = get_object_or_404(Request, pk=pk)
    # Check if the current user has already left feedback
    user_has_reviewed = req.reviews.filter(reviewer=request.user).exists()
    return render(request, 'assist_requests/request_detail.html', {
        'request_obj': req,
        'user_has_reviewed': user_has_reviewed,
    })


from django.utils import timezone
from django.conf import settings


@login_required
def request_accept(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if request.user.role != 'volunteer':
        messages.error(request, 'Only volunteers can accept requests.')
        return redirect('assist_requests:request_detail', pk=pk)

    if req.status != 'open':
        messages.error(request, 'This request is no longer open.')
        return redirect('assist_requests:request_detail', pk=pk)

    # ── Phase 6 Verification Gating ───────────────────────────────────────
    gating_cfg = getattr(settings, 'VERIFICATION_GATING_SETTINGS', {})
    require_in_person = gating_cfg.get('REQUIRE_VERIFICATION_IN_PERSON', True)
    low_risk_cats = [c.lower() for c in gating_cfg.get('LOW_RISK_CATEGORIES', ['tech support'])]

    is_in_person_req = False
    if req.category:
        cat_name = req.category.name.lower()
        if req.category.is_in_person or (not any(lr in cat_name for lr in low_risk_cats)):
            is_in_person_req = True

    if require_in_person and is_in_person_req and not request.user.is_verified:
        messages.error(
            request,
            'This assistance category requires volunteer verification. '
            'Unverified volunteers can accept low-risk tasks (such as Tech Support). '
            'Please contact staff or wait for your account verification to accept in-person requests.'
        )
        return redirect('assist_requests:request_detail', pk=pk)

    req.status = 'assigned'
    req.volunteer = request.user
    req.accepted_at = timezone.now()
    req.save(update_fields=['status', 'volunteer', 'accepted_at'])

    # Notify the requester
    _create_notification(
        req.user,
        f'Your request "{req.title}" has been accepted by volunteer {request.user.username}!'
    )

    messages.success(request, f'You have successfully accepted: {req.title}')
    return redirect('assist_requests:request_detail', pk=pk)


@login_required
def request_complete(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if request.user != req.volunteer:
        messages.error(request, 'Only the assigned volunteer can mark this complete.')
        return redirect('assist_requests:request_detail', pk=pk)

    req.status = 'completed'
    req.completed_at = timezone.now()
    req.save(update_fields=['status', 'completed_at'])

    # Award 10 points to the volunteer and check for certificate milestones
    try:
        profile = request.user.volunteer_profile
        profile.points += 10
        profile.save()

        # Auto-award certificates at milestones
        from rewards.models import Certificate
        milestones = [
            (200, 'Gold Certificate of Excellence'),
            (100, 'Silver Certificate of Achievement'),
            (50,  'Bronze Certificate of Participation'),
        ]
        for threshold, title in milestones:
            if profile.points >= threshold and not Certificate.objects.filter(user=request.user, title=title).exists():
                Certificate.objects.create(user=request.user, title=title)
                _create_notification(request.user, f'🏆 Congratulations! You earned the {title}!')
                break

    except Exception:
        pass

    # Notify the requester that the task is complete
    _create_notification(
        req.user,
        f'Your request "{req.title}" has been marked as completed by {request.user.username}. Please leave a review!'
    )

    messages.success(request, 'Request marked as completed! You earned 10 points.')
    return redirect('assist_requests:request_detail', pk=pk)


@login_required
def request_cancel(request, pk):
    req = get_object_or_404(Request, pk=pk)

    is_requester = (request.user == req.user)
    is_assigned_vol = (request.user == req.volunteer and req.status == 'assigned')

    if not (is_requester or is_assigned_vol):
        messages.error(request, 'You do not have permission to cancel or withdraw from this request.')
        return redirect('assist_requests:request_detail', pk=pk)

    if req.status not in ('open', 'assigned'):
        messages.error(request, 'This request cannot be cancelled.')
        return redirect('assist_requests:request_detail', pk=pk)

    reason = request.POST.get('cancellation_reason', '').strip() if request.method == 'POST' else ''

    if is_assigned_vol:
        # Volunteer withdrawal: returns request to Open and records withdrawal
        req.status = 'open'
        req.volunteer = None
        req.is_volunteer_withdrawal = True
        req.cancellation_reason = reason or 'Volunteer withdrew from assignment'
        req.cancelled_at = timezone.now()
        req.cancelled_by = request.user
        req.save(update_fields=['status', 'volunteer', 'is_volunteer_withdrawal', 'cancellation_reason', 'cancelled_at', 'cancelled_by'])

        _create_notification(
            req.user,
            f'Volunteer {request.user.username} withdrew from your request "{req.title}". It has been reopened for other volunteers.'
        )
        messages.warning(request, 'You have withdrawn from this request. It is now open for other volunteers.')
        return redirect('assist_requests:request_list')

    else:
        # Requester cancellation
        req.status = 'cancelled'
        req.cancelled_at = timezone.now()
        req.cancelled_by = request.user
        req.cancellation_reason = reason or 'Cancelled by requester'
        req.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancellation_reason'])

        if req.volunteer:
            _create_notification(
                req.volunteer,
                f'The request "{req.title}" was cancelled by the requester.'
            )

        messages.success(request, 'Your request has been cancelled.')
        return redirect('assist_requests:request_list')
