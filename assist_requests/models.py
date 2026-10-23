from django.db import models
from accounts.models import CustomUser


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_in_person = models.BooleanField(
        default=False,
        help_text="In-person categories require volunteer verification."
    )

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Request(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_requests')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    title = models.CharField(max_length=200)
    description = models.TextField()
    required_skills = models.TextField(help_text="Comma separated skills")
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    volunteer = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Phase 6 Timing & Cancellation / Withdrawal Tracking ──────────────
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cancelled_requests'
    )
    cancellation_reason = models.TextField(blank=True)
    is_volunteer_withdrawal = models.BooleanField(
        default=False,
        help_text="Whether this cancellation was a volunteer backing out"
    )

    # ── Soft-delete / archive ─────────────────────────────────────────────
    is_archived = models.BooleanField(default=False, db_index=True,
                                      help_text="Archived requests are hidden by default but data is preserved.")
    archived_at = models.DateTimeField(null=True, blank=True)
    archive_reason = models.TextField(blank=True)

    def __str__(self):
        return self.title

