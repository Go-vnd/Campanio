from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Profile

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role", "password1", "password2")

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("bio", "accessibility_preferences", "service_radius_miles")
