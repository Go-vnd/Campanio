from django import forms
from .models import AssistanceRequest, Feedback

class AssistanceRequestForm(forms.ModelForm):
    class Meta:
        model = AssistanceRequest
        fields = ("category", "title", "description", "scheduled_at", "interaction_mode",
                  "location", "accessibility_instructions", "priority")
        widgets = {"scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ("rating", "testimonial")
