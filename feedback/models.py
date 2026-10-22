from django.db import models
from accounts.models import CustomUser
from assist_requests.models import Request


class Review(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Phase 4 Moderation & Flagging ─────────────────────────────────────────
    is_flagged = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False, help_text="Hide abusive or inappropriate review text")
    hidden_reason = models.TextField(blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Review by {self.reviewer.username} — {self.rating}★"

