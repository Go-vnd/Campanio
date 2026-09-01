import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'companio.settings')
django.setup()

from django.contrib.auth import authenticate
from accounts.models import User

# Test authentication
user = authenticate(username='volunteer', password='volunteer123')
if user:
    print(f'✓ Authentication successful')
    print(f'  Username: {user.username}')
    print(f'  Role: {user.role}')
    print(f'  Is active: {user.is_active}')
else:
    print('✗ Authentication failed')
    print('\nTrying to check password hash manually...')
    vol = User.objects.get(username='volunteer')
    
    # Try checking password
    from django.contrib.auth.hashers import check_password
    pwd_check = check_password('volunteer123', vol.password)
    print(f'Password "volunteer123" matches: {pwd_check}')
    
    # List all users and passwords for debugging
    print('\nAll users in database:')
    for u in User.objects.all():
        is_usable = u.password != '!'
        print(f'  {u.username} - password usable: {is_usable}')
