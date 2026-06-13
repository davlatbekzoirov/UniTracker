from decimal import Decimal
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import University, Scholarship, Document, TestScore, ApplicationTask, DocumentVersion

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

    def clean(self):
        data = super().clean()

        sat_r = data.get('sat_reading')
        sat_m = data.get('sat_math')
        if sat_r is not None and sat_r % 10 != 0:
            self.add_error('sat_reading', 'SAT scores are reported in 10-point increments (e.g. 650, 720).')
        if sat_m is not None and sat_m % 10 != 0:
            self.add_error('sat_math', 'SAT scores are reported in 10-point increments (e.g. 650, 720).')

        ielts_fields = ['ielts_overall', 'ielts_listening', 'ielts_reading', 'ielts_writing', 'ielts_speaking']
        ielts_values = {f: data.get(f) for f in ielts_fields if data.get(f) is not None}

        for field, val in ielts_values.items():
            if val * 2 != int(val * 2):
                self.add_error(field, 'IELTS bands must be in 0.5 increments (e.g. 6.0, 6.5, 7.0).')

        skill_fields = ['ielts_listening', 'ielts_reading', 'ielts_writing', 'ielts_speaking']
        skill_values = [data.get(f) for f in skill_fields if data.get(f) is not None]
        overall = data.get('ielts_overall')

        if overall is not None and skill_values:
            avg = sum(skill_values) / len(skill_values)
            rounded_avg = Decimal(str(round(float(avg) * 2) / 2))

            if overall > rounded_avg + Decimal('0.5'):
                self.add_error(
                    'ielts_overall',
                    f'Overall band ({overall}) is too high given your section scores '
                    f'(expected {rounded_avg} based on the mean of your skills).'
                )
            elif overall < rounded_avg - Decimal('0.5'):
                self.add_error(
                    'ielts_overall',
                    f'Overall band ({overall}) is too low given your section scores '
                    f'(expected {rounded_avg} based on the mean of your skills).'
                )

        toefl_sections = ['toefl_reading', 'toefl_listening', 'toefl_speaking', 'toefl_writing']
        section_values = [data.get(f) for f in toefl_sections if data.get(f) is not None]
        toefl_total    = data.get('toefl_total')

        if toefl_total is not None and section_values:
            expected_total = sum(section_values)
            if len(section_values) == 4 and toefl_total != expected_total:
                self.add_error(
                    'toefl_total',
                    f'TOEFL total ({toefl_total}) must equal the sum of your four section scores '
                    f'({" + ".join(str(v) for v in section_values)} = {expected_total}).'
                )
            elif toefl_total > expected_total and len(section_values) == 4:
                self.add_error('toefl_total', f'Total cannot exceed the sum of section scores ({expected_total}).')

        return data

class ApplicationTaskForm(forms.ModelForm):
    class Meta:
        model  = ApplicationTask          # noqa — imported above
        fields = ['title', 'task_type', 'status', 'due_date', 'notes', 'order']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes':    forms.Textarea(attrs={'rows': 2}),
        }

class DocumentVersionForm(forms.ModelForm):
    class Meta:
        model  = DocumentVersion
        fields = ['label', 'file', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'label': forms.TextInput(attrs={'placeholder': 'e.g. Draft 1, Revised, Final'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].validators.append(validate_pdf_and_size)