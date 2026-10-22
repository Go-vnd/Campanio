from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, Profile


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'role')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role')


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'skills', 'location', 'availability', 'profile_picture')
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Tell others a bit about yourself...',
            }),
            'skills': forms.TextInput(attrs={
                'placeholder': 'e.g., Reading, Driving, Sign Language, Coding',
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'e.g., Downtown Seattle, Brooklyn NY, Austin TX',
            }),
            'availability': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g., Weekday evenings, Weekend mornings',
            }),
        }
        labels = {
            'skills': 'Skills (comma-separated)',
            'location': 'Location / Neighborhood',
            'availability': 'Availability',
            'profile_picture': 'Profile Picture',
        }
