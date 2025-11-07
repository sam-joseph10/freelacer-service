# forms.py
from django import forms
from .models import *

class CertificatePostForm(forms.ModelForm):
    class Meta:
        model = CertificatePost
        fields = ["certificate", "caption"]
        widgets = {
            "caption": forms.Textarea(attrs={"rows": 3, "placeholder": "Enter caption..."}),
        }


from django import forms
from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'description', 'skills_required', 'experience_level', 'salary', 'deadline', 'job_type']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter job title'}),
            'description': forms.Textarea(attrs={'placeholder': 'Enter job description'}),
            'skills_required': forms.TextInput(attrs={'placeholder': 'Enter required skills'}),
            'experience_level': forms.Select(choices=[
                ('Fresher', 'Fresher'),
                ('Mid-Level', 'Mid-Level'),
                ('Senior', 'Senior')
            ]),
            'salary': forms.NumberInput(attrs={'placeholder': 'Enter pay or salary'}),
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'job_type': forms.Select(attrs={'placeholder': 'Select job type'}, choices=[
                ('full_time', 'Full-time'),
                ('part_time', 'Part-time'),
                ('internship', 'Internship')
            ]),
        }


class RecruiterProfileForm(forms.ModelForm):
    class Meta:
        model = RecruiterProfile
        fields = ['company_name', 'company_description', 'phone', 'location']

class AIRequestForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Type your question here...', 'rows': 3}),
        required=True
    )
    resume = forms.FileField(required=False)
