from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        SEEKER = "seeker", "Assistance Seeker"
        VOLUNTEER = "volunteer", "Volunteer Helper"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SEEKER)
    phone = models.CharField(max_length=30, blank=True)
    is_verified = models.BooleanField(default=False)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True)
    accessibility_preferences = models.JSONField(default=dict, blank=True)
    service_radius_miles = models.PositiveIntegerField(default=10)
    background_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile: {self.user.username}"

class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    role = models.CharField(max_length=50, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name} ({self.email})"
