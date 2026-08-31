from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import RegisterForm, ProfileForm
from .models import Profile

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
    if request.user.role == "admin": return redirect("admin_dashboard")
    if request.user.role == "volunteer": return redirect("volunteer_dashboard")
    return render(request, "user/dashboard.html")

@login_required
def profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile)
    template_name = "volunteer/profile.html" if request.user.role == "volunteer" else "user/profile.html"
    return render(request, template_name, {"form": form})
