from django.db import models
from django.conf import settings


class AdminAuditLog(models.Model):
    """
    Records every admin action that changes data.
    All destructive / data-changing dashboard actions must create an entry here.
    """
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)          # e.g. "deactivate_user"
    target_type = models.CharField(max_length=60)      # e.g. "User", "Request"
    target_id = models.CharField(max_length=40, blank=True)
    target_repr = models.CharField(max_length=255, blank=True)  # human label
    reason = models.TextField(blank=True)
    extra = models.JSONField(default=dict, blank=True)  # any extra context
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Admin Audit Log'
        verbose_name_plural = 'Admin Audit Logs'

    def __str__(self):
        return (
            f"[{self.timestamp:%Y-%m-%d %H:%M}] "
            f"{self.staff} \u2192 {self.action} {self.target_type}#{self.target_id}"
        )


class Report(models.Model):
    TYPE_CHOICES = (
        ('platform_suggestion', 'Platform Suggestion'),
        ('general_complaint', 'General Complaint'),
        ('report_volunteer', 'Report about a Volunteer'),
        ('report_user', 'Report about a User'),
    )

    CATEGORY_CHOICES = (
        ('unsafe_behavior', 'Unsafe behavior'),
        ('no_show', 'No-show'),
        ('rude_disrespectful', 'Rude or disrespectful'),
        ('asked_money_or_info', 'Asked for money or personal info'),
        ('poor_quality_help', 'Poor quality help'),
        ('other', 'Other'),
    )

    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )

    STATUS_CHOICES = (
        ('new', 'New'),
        ('in_review', 'In review'),
        ('action_taken', 'Action taken'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    )

    report_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general_complaint')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='filed_reports',
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_reports',
    )
    related_request = models.ForeignKey(
        'assist_requests.Request',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
    )
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_reports',
    )
    reference_number = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'

    def save(self, *args, **kwargs):
        if not self.reference_number:
            import uuid
            self.reference_number = f"REP-{uuid.uuid4().hex[:8].upper()}"
        # Safety categories default to high severity
        if self.category in ['unsafe_behavior', 'asked_money_or_info'] and self.severity != 'high':
            self.severity = 'high'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.reference_number}] {self.get_category_display()} ({self.get_status_display()})"


class ReportNote(models.Model):
    """Internal staff notes on a report."""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='notes')
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Note by {self.staff} on {self.report.reference_number}"


class ReportStatusHistory(models.Model):
    """Audit trail of status transitions for a report."""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='status_history')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.report.reference_number}: {self.old_status} -> {self.new_status}"

