from django.db import models
from django.contrib.auth.models import User


class TestScore(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='test_scores')
    sat_reading = models.PositiveSmallIntegerField(null=True, blank=True)
    sat_math = models.PositiveSmallIntegerField(null=True, blank=True)
    ielts_overall = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    ielts_listening = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    ielts_reading = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    ielts_writing = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    ielts_speaking = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    toefl_total = models.PositiveSmallIntegerField(null=True, blank=True)
    toefl_reading = models.PositiveSmallIntegerField(null=True, blank=True)
    toefl_listening = models.PositiveSmallIntegerField(null=True, blank=True)
    toefl_speaking = models.PositiveSmallIntegerField(null=True, blank=True)
    toefl_writing = models.PositiveSmallIntegerField(null=True, blank=True)

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
        from django.utils import timezone
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


def document_upload_path(instance, filename):
    return f'documents/{instance.user.id}/{filename}'


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
    file = models.FileField(upload_to=document_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_doc_type_display()})"
