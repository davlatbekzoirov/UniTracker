from django.contrib import admin

from .models import University, Scholarship, Document, TestScore

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'program', 'university_type', 'status', 'deadline', 'user']
    list_filter = ['status', 'university_type', 'country']
    search_fields = ['name', 'program']

@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ['name', 'university', 'amount', 'currency', 'applied']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'doc_type', 'university', 'user', 'uploaded_at']

@admin.register(TestScore)
class TestScoreAdmin(admin.ModelAdmin):
    list_display = ['user', 'sat_reading', 'sat_math', 'ielts_overall', 'toefl_total']

