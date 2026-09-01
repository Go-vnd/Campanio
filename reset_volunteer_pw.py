import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'companio.settings')
django.setup()

from accounts.models import User

# Reset volunteer password
volunteer = User.objects.get(username='volunteer')
volunteer.set_password('volunteer123')
volunteer.save()

print(f'✓ Password reset for volunteer')
print(f'  Username: {volunteer.username}')
print(f'  New password hash: {volunteer.password[:30]}...')

# Test authentication
from django.contrib.auth import authenticate
user = authenticate(username='volunteer', password='volunteer123')
if user:
    print(f'\n✓ Authentication test successful')
else:
    print(f'\n✗ Authentication test failed')
