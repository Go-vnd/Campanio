from django.db import models
from accounts.models import CustomUser

class Certificate(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='certificates')
    title = models.CharField(max_length=200)
    issue_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='certificates/', blank=True, null=True)

    def __str__(self):
        return f"{self.title} for {self.user.username}"


class Badge(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, help_text="Emoji or icon class")
    description = models.TextField()

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')

    def __str__(self):
        return f"{self.badge.name} awarded to {self.user.username}"
