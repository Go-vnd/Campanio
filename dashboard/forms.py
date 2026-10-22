from django import forms
from .models import Report


class ReportSubmissionForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ('category', 'description')
        widgets = {
            'category': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional: Tell us what happened in your own words...',
                'aria-label': 'Description of what happened'
            }),
        }
        labels = {
            'category': 'What happened? (Select the closest reason)',
            'description': 'Additional details (optional)',
        }
