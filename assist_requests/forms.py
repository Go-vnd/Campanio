from django import forms
from .models import Request


class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ('title', 'category', 'priority', 'description', 'required_skills', 'location')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'required_skills': forms.TextInput(
                attrs={'placeholder': 'e.g., Reading, Driving, Sign Language'}
            ),
        }
