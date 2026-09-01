import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'companio.settings')
import django
django.setup()

from accounts.models import User
from assistance.models import AssistanceRequest
from notifications.models import Notification

print('Database Summary:')
print(f'  Total Users: {User.objects.count()}')
print(f'    - Admins: {User.objects.filter(role="admin").count()}')
print(f'    - Volunteers: {User.objects.filter(role="volunteer").count()}')
print(f'    - Seekers: {User.objects.filter(role="seeker").count()}')
print(f'  Assistance Requests: {AssistanceRequest.objects.count()}')
print(f'  Notifications: {Notification.objects.count()}')
