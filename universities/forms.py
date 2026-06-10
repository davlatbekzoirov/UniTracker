from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import University, Scholarship, Document, TestScore

def validate_pdf_and_size(file):
    """
    Validates that a file is a PDF and does not exceed 5MB.
    """
    max_size = 5 * 1024 * 1024 
    if file.size > max_size:
        raise ValidationError("File size cannot exceed 5MB.")
        
    if not file.name.lower().endswith('.pdf'):
        raise ValidationError("Only PDF documents are allowed.")
        
    file.seek(0)
    header = file.read(4)
    if header != b'%PDF':
        raise ValidationError("Invalid file format. The file is corrupted or not a true PDF.")
    
    return file

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class UniversityForm(forms.ModelForm):
    class Meta:
        model = University
        fields = ['name', 'country', 'program', 'university_type', 'status', 'deadline', 'notes', 'website']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class ScholarshipForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = ['name', 'amount', 'currency', 'deadline', 'applied', 'notes']
        widgets = {'deadline': forms.DateInput(attrs={'type': 'date'})}


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['university', 'doc_type', 'name', 'file', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['university'].queryset = University.objects.filter(user=user)
        self.fields['university'].required = False
        
        self.fields['file'].validators.append(validate_pdf_and_size)


class TestScoreForm(forms.ModelForm):
    class Meta:
        model = TestScore
        exclude = ['user']
        labels = {
            'sat_reading': 'SAT Reading & Writing', 'sat_math': 'SAT Math',
            'ielts_overall': 'IELTS Overall', 'ielts_listening': 'Listening',
            'ielts_reading': 'Reading', 'ielts_writing': 'Writing',
            'ielts_speaking': 'Speaking', 'toefl_total': 'TOEFL Total',
            'toefl_reading': 'Reading', 'toefl_listening': 'Listening',
            'toefl_speaking': 'Speaking', 'toefl_writing': 'Writing',
        }
