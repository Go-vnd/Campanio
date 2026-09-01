import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'companio.settings')
django.setup()

from accounts.models import User

volunteer = User.objects.filter(username='volunteer').first()
if volunteer:
    print(f'Volunteer exists: {volunteer.username}')
    print(f'Email: {volunteer.email}')
    print(f'Role: {volunteer.role}')
    print(f'Is active: {volunteer.is_active}')
    print(f'Is staff: {volunteer.is_staff}')
    print(f'Password hash: {volunteer.password[:20]}...')
else:
    print('Volunteer user not found')
    print('\nAvailable users:')
    for user in User.objects.all():
        print(f'  - {user.username} (role: {user.role}, active: {user.is_active})')
