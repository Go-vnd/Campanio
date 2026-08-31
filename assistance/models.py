from django.conf import settings
from django.db import models

class AssistanceRequest(models.Model):
    class Category(models.TextChoices):
        MOBILITY = "mobility", "Mobility & Escort Assistance"
        SIGN = "sign", "Sign Language Interpretation"
        READING = "reading", "Audio & Document Reading"
        TECH = "tech", "Assistive Technology Guidance"
        COMPANIONSHIP = "companionship", "Social Companionship"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        MATCHED = "matched", "Matched"
        ACCEPTED = "accepted", "Accepted"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        URGENT = "urgent", "Urgent"

    seeker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assistance_requests")
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="accepted_requests")
    category = models.CharField(max_length=30, choices=Category.choices)
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    interaction_mode = models.CharField(max_length=50, default="virtual")
    location = models.CharField(max_length=255, blank=True)
    accessibility_instructions = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"REQ-{self.pk}: {self.title}"

class Feedback(models.Model):
    request = models.OneToOneField(AssistanceRequest, on_delete=models.CASCADE, related_name="feedback")
    seeker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_feedback")
    rating = models.PositiveSmallIntegerField()
    testimonial = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="rating_1_to_5")
        ]
