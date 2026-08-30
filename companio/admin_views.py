from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
def admin_required(view):
 @login_required
 def wrapped(request,*args,**kwargs):
  if request.user.role != "admin" and not request.user.is_staff: raise PermissionDenied
  return view(request,*args,**kwargs)
 return wrapped
@admin_required
def admin_dashboard(request): return render(request,"admin/dashboard.html")
@admin_required
def admin_users(request): return render(request,"admin/users.html")
@admin_required
def admin_volunteers(request): return render(request,"admin/volunteers.html")
@admin_required
def admin_requests(request): return render(request,"admin/requests.html")
@admin_required
def admin_analytics(request): return render(request,"admin/analytics.html")
@admin_required
def admin_badges(request): return render(request,"admin/badges.html")
