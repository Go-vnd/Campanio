from django.conf import settings
from django.db import models

class Skill(models.Model):
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    verified = models.BooleanField(default=False)
    certification_document = models.FileField(upload_to="skill_certifications/", blank=True, null=True)
    requests_fulfilled = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.volunteer.username}: {self.name}"

class Availability(models.Model):
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability")
    day_of_week = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]

class VolunteerStats(models.Model):
    volunteer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="volunteer_stats")
    hours_contributed = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    tasks_completed = models.PositiveIntegerField(default=0)
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    reward_points = models.PositiveIntegerField(default=0)
