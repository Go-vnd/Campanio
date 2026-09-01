import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'companio.settings')
django.setup()

from assistance.models import AssistanceRequest
from accounts.models import User

# Test Admin Dashboard
print('=== ADMIN DASHBOARD DATA ===')
print(f'Total Users (Seekers): {User.objects.filter(role="seeker").count()}')
print(f'Total Volunteers: {User.objects.filter(role="volunteer").count()}')
print(f'Total Requests: {AssistanceRequest.objects.count()}')
print(f'Pending Requests: {AssistanceRequest.objects.filter(status="pending").count()}')
print(f'Completed Requests: {AssistanceRequest.objects.filter(status="completed").count()}')
print(f'Accepted Requests: {AssistanceRequest.objects.filter(status="accepted").count()}')

# Test Seeker Dashboard (user1)
print('\n=== SEEKER DASHBOARD (user1) ===')
seeker = User.objects.get(username='user1')
requests = AssistanceRequest.objects.filter(seeker=seeker)
print(f'Total Requests: {requests.count()}')
print(f'Pending: {requests.filter(status="pending").count()}')
print(f'Accepted: {requests.filter(status="accepted").count()}')
print(f'Completed: {requests.filter(status="completed").count()}')
print(f'Recent: {[t.title for t in requests[:3]]}')

# Test Volunteer Dashboard
print('\n=== VOLUNTEER DASHBOARD ===')
volunteer = User.objects.get(username='volunteer')
vol_tasks = AssistanceRequest.objects.filter(volunteer=volunteer)
print(f'Total Assigned Tasks: {vol_tasks.count()}')
print(f'Completed Tasks: {vol_tasks.filter(status="completed").count()}')
print(f'Active Tasks: {vol_tasks.filter(status="accepted").count()}')
print(f'Requests: {[t.title for t in vol_tasks]}')
