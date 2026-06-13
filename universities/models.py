import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class TestScore(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='test_scores')

    # SAT: each section 200–800
    sat_reading = models.PositiveSmallIntegerField(null=True, blank=True,
        validators=[MinValueValidator(200), MaxValueValidator(800)])
    sat_math    = models.PositiveSmallIntegerField(null=True, blank=True,
        validators=[MinValueValidator(200), MaxValueValidator(800)])

    ielts_overall   = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(9.0)])
    ielts_listening = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(9.0)])
    ielts_reading   = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(9.0)])
    ielts_writing   = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(9.0)])
    ielts_speaking  = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(9.0)])

    toefl_total     = models.PositiveSmallIntegerField(null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(120)])
    toefl_reading   = models.PositiveSmallIntegerField(null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(30)])
    toefl_listening = models.PositiveSmallIntegerField(null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(30)])
    toefl_speaking  = models.PositiveSmallIntegerField(null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(30)])
    toefl_writing   = models.PositiveSmallIntegerField(null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(30)])

    def __str__(self):
        return f"{self.user.username}'s scores"

    @property
    def sat_total(self):
        r = self.sat_reading or 0
        m = self.sat_math or 0
        return r + m if (r or m) else None

class University(models.Model):
    TYPE_CHOICES = [('reach','Reach'),('match','Match'),('safety','Safety')]
    STATUS_CHOICES = [
        ('preparing','Preparing'),('submitted','Submitted'),
        ('interview','Interview'),('accepted','Accepted'),
        ('rejected','Rejected'),('deferred','Deferred'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='universities')
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    program = models.CharField(max_length=200)
    university_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='match')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='preparing')
    deadline = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deadline']
        verbose_name_plural = 'universities'

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def days_until_deadline(self):
        if not self.deadline:
            return None
        return (self.deadline - timezone.now().date()).days

class Scholarship(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='scholarships')
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=5, default='USD')
    deadline = models.DateField(null=True, blank=True)
    applied = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} – {self.university.name}"

def validate_pdf_and_size(file):
    """
    Ensures the file is a true PDF and is under 5MB at the database layer.
    """
    max_size = 5 * 1024 * 1024 
    if file.size > max_size:
        raise ValidationError("File size cannot exceed 5MB.")
        
    if not file.name.lower().endswith('.pdf'):
        raise ValidationError("Only PDF documents are allowed.")
        
    file.seek(0)
    header = file.read(4)
    if header != b'%PDF':
        raise ValidationError("Invalid file format. This file is not a valid PDF.")
    return file

def document_upload_path(instance, filename):
    user_id = getattr(instance, 'user_id', None)
    if user_id is None:                       
        user_id = instance.document.user_id
    return f'documents/{user_id}/{filename}'

class Document(models.Model):
    DOC_TYPES = [
        ('sop','Statement of Purpose'),('lor','Letter of Recommendation'),
        ('transcript','Transcript'),('cv','CV / Resume'),
        ('essay','Essay'),('other','Other'),
    ]
    university = models.ForeignKey(University, on_delete=models.CASCADE,
                                   related_name='documents', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    name = models.CharField(max_length=200)
    
    file = models.FileField(upload_to=document_upload_path, validators=[validate_pdf_and_size])
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_doc_type_display()})"
    
class ApplicationTask(models.Model):

    TASK_TYPE_CHOICES = [
        ('sop',        'Statement of Purpose'),
        ('lor',        'Letter of Recommendation'),
        ('transcript', 'Official Transcripts'),
        ('cv',         'CV / Resume'),
        ('essay',      'Supplemental Essay'),
        ('test_score', 'Test Score Submission'),
        ('financials', 'Financial Documents'),
        ('visa',       'Visa / Immigration Docs'),
        ('other',      'Other'),
    ]

    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('in_progress', 'In Progress'),
        ('done',        'Done'),
    ]

    # Every task belongs to exactly one university application
    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name='tasks',
    )

    title     = models.CharField(max_length=200)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default='other')
    status    = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    due_date  = models.DateField(null=True, blank=True)
    notes     = models.TextField(blank=True)
    order     = models.PositiveSmallIntegerField(default=0)  # controls display order

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"[{self.university.name}] {self.title} ({self.get_status_display()})"

    @property
    def is_done(self):
        return self.status == 'done'
    
_CORE_TASKS = [
    (1,  'sop',        'Draft Statement of Purpose'),
    (2,  'sop',        'Finalise & Proofread SOP'),
    (3,  'lor',        'Ask Professor / Employer for LOR 1'),
    (4,  'lor',        'Ask Professor / Employer for LOR 2'),
    (5,  'transcript', 'Request Official Transcripts'),
    (6,  'cv',         'Update CV / Resume'),
    (7,  'test_score', 'Submit Test Scores (SAT / IELTS / TOEFL)'),
]

_MATCH_EXTRA = [
    (8,  'essay',      'Write Supplemental Essay'),
    (9,  'financials', 'Prepare Financial / Bank Documents'),
]

_REACH_EXTRA = [
    (10, 'essay',      'Write Short-Answer Essays'),
    (11, 'financials', 'Obtain Sponsorship / Scholarship Proof'),
    (12, 'visa',       'Start Visa / I-20 Preparation'),
]

TASK_TEMPLATES = {
    'safety': _CORE_TASKS,
    'match':  _CORE_TASKS + _MATCH_EXTRA,
    'reach':  _CORE_TASKS + _MATCH_EXTRA + _REACH_EXTRA,
}

def generate_tasks_for_university(university: University) -> None:
    """
    Creates the default ApplicationTask rows for a university.
    Safe to call multiple times — skips creation if tasks already exist.
    """
    if university.tasks.exists():
        return  

    templates = TASK_TEMPLATES.get(university.university_type, _CORE_TASKS)
    tasks = [
        ApplicationTask(
            university=university,
            order=order,
            task_type=task_type,
            title=title,
        )
        for order, task_type, title in templates
    ]
    ApplicationTask.objects.bulk_create(tasks)

class DocumentVersion(models.Model):
    document   = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    file       = models.FileField(upload_to=document_upload_path, validators=[validate_pdf_and_size])
    label      = models.CharField(max_length=100, default='Draft',
                     help_text='e.g. "Draft 1", "Revised", "Final"')
    notes      = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                     null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f'{self.document.name} — {self.label}'

def share_link_expiry():
    return timezone.now() + timezone.timedelta(days=7)

class ShareLink(models.Model):
    document   = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='share_links')
    token      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=share_link_expiry)
    is_active  = models.BooleanField(default=True)
    accessed_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'Share link for {self.document.name} (expires {self.expires_at:%Y-%m-%d})'

    @property
    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at

class CalendarToken(models.Model):
    user  = models.OneToOneField(User, on_delete=models.CASCADE, related_name='calendar_token')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return f"{self.user.username} calendar token"

    @classmethod
    def get_or_create_for(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj