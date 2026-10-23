from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('volunteer', 'Volunteer'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='user')
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_volunteers'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"



class Profile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='volunteer_profile'
    )
    skills = models.TextField(blank=True, help_text="Comma separated skills")
    availability = models.TextField(blank=True)
    points = models.IntegerField(default=0)
    certificates_earned = models.IntegerField(default=0)
    location = models.CharField(max_length=150, blank=True, help_text="City, neighborhood, or area")
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    a11y_settings = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
