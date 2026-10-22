from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .forms import CustomUserCreationForm, ProfileEditForm
from .models import Profile


def register_view(request):
    if request.user.is_authenticated:
        return redirect('assist_requests:request_list')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f'Welcome to Companio, {user.username}!')
            return redirect('assist_requests:request_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard:dashboard_home')
        return redirect('assist_requests:request_list')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', None)
            if next_url:
                return redirect(next_url)
            if user.is_staff:
                return redirect('dashboard:dashboard_home')
            return redirect('assist_requests:request_list')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {'profile': profile})


@login_required
def profile_edit_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, 'accounts/profile_edit.html', {'form': form, 'profile': profile})


@login_required
@require_POST
def a11y_save(request):
    """Save accessibility settings (font size, color filter, etc.) for the logged-in user."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.a11y_settings = data
    profile.save(update_fields=['a11y_settings'])
    return JsonResponse({'status': 'ok'})


@login_required
def a11y_load(request):
    """Return the saved accessibility settings for the logged-in user."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return JsonResponse(profile.a11y_settings or {})
