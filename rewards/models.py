from django.conf import settings
from django.db import models

class Badge(models.Model):
    title = models.CharField(max_length=120)
    criteria = models.TextField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class BadgeAward(models.Model):
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badge_awards")
    awarded_at = models.DateTimeField(auto_now_add=True)

class Certificate(models.Model):
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    title = models.CharField(max_length=200, default="Certificate of Excellence")
    hours_recognized = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    certificate_id = models.CharField(max_length=80, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
