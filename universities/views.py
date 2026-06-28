import json as _json
import os
import uuid as _uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Case, When, Value, CharField
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_POST
from .models import University, Scholarship, Document, TestScore, ApplicationTask, DocumentVersion, ShareLink, CalendarToken
from .forms  import UniversityForm, ScholarshipForm, DocumentForm, TestScoreForm, ApplicationTaskForm, DocumentVersionForm

@login_required
def dashboard(request):
    universities = University.objects.filter(user=request.user)
    today = timezone.now().date()
    upcoming = universities.filter(deadline__gte=today).order_by('deadline')[:5]
    
    scholarships = Scholarship.objects.filter(university__user=request.user)
    
    EXCHANGE_RATES = {'USD': 1.0, 'EUR': 1.08, 'GBP': 1.27} 
    
    total_applied_usd = Decimal('0.00')
    total_awarded_usd = Decimal('0.00')
    
    for s in scholarships:
        if s.amount:
            rate = Decimal(str(EXCHANGE_RATES.get(s.currency, 1.0)))
            amount_in_usd = s.amount * rate 
            
            if s.applied:
                total_applied_usd += amount_in_usd
            if s.university.status == 'accepted':
                total_awarded_usd += amount_in_usd

    stats = {
        'total': universities.count(),
        'submitted': universities.filter(status__in=['submitted','interview','accepted','deferred']).count(),
        'accepted': universities.filter(status='accepted').count(),
        'interview': universities.filter(status='interview').count(),
        'due_soon': universities.filter(deadline__gte=today, deadline__lte=today + timezone.timedelta(days=30)).count(),
        'reach': universities.filter(university_type='reach').count(),
        'match': universities.filter(university_type='match').count(),
        'safety': universities.filter(university_type='safety').count(),
        'total_applied_usd': round(total_applied_usd, 2),
        'total_awarded_usd': round(total_awarded_usd, 2),
    }
    
    try:
        scores = request.user.test_scores
    except TestScore.DoesNotExist:
        scores = None
        
    timeline_labels = []
    timeline_data   = []
    for uni in universities.filter(deadline__isnull=False).order_by('deadline'):
        timeline_labels.append(uni.name)
        timeline_data.append(uni.deadline.isoformat())

    app_fee_total_usd = Decimal('0.00') 
    status_labels  = ['Reach', 'Match', 'Safety']
    status_counts  = [stats['reach'], stats['match'], stats['safety']]

    return render(request, 'applications/dashboard.html', {
        'universities': universities, 'upcoming': upcoming,
        'stats': stats, 'scores': scores,
        'timeline_labels_json': _json.dumps(timeline_labels),
        'timeline_dates_json':  _json.dumps(timeline_data),
        'status_counts_json':   _json.dumps(status_counts),
        'scholarship_applied':  float(stats['total_applied_usd']),
        'scholarship_awarded':  float(stats['total_awarded_usd']),
    })

@login_required
def university_list(request):
    qs = University.objects.filter(user=request.user)
    
    try:
        user_scores = request.user.test_scores
        user_sat = user_scores.sat_total or 0
        user_ielts = user_scores.ielts_overall or 0
    except TestScore.DoesNotExist:
        user_sat = 0
        user_ielts = 0

    qs = qs.annotate(
        admission_chance=Case(
            When(university_type='safety', then=Value('High Probability')),
            When(Q(university_type='match') & (Q(id__isnull=False) if user_sat >= 1400 or user_ielts >= 7.5 else Q(id__isnull=True)), then=Value('High Probability')),
            When(university_type='reach', then=Value('Reach / Competitive')),
            default=Value('Standard Match'),
            output_field=CharField(),
        )
    )

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
        
    return render(request, 'applications/university_list.html', {
        'universities': qs, 
        'status_filter': status_filter,
    })

@login_required
def university_create(request):
    form = UniversityForm(request.POST or None)
    if form.is_valid():
        uni = form.save(commit=False)
        uni.user = request.user
        uni.save()
        messages.success(request, f'{uni.name} added.')
        return redirect('universities:university_list')
    return render(request, 'applications/university_form.html', {'form': form, 'action': 'Add'})

@login_required
def university_edit(request, pk):
    uni = get_object_or_404(University, pk=pk, user=request.user)
    form = UniversityForm(request.POST or None, instance=uni)
    if form.is_valid():
        form.save()
        messages.success(request, 'Updated.')
        return redirect('universities:university_list')
    return render(request, 'applications/university_form.html', {
        'form': form, 'action': 'Edit', 'uni': uni,
    })

@login_required
def university_delete(request, pk):
    uni = get_object_or_404(University, pk=pk, user=request.user)
    if request.method == 'POST':
        uni.delete()
        messages.success(request, f'{uni.name} removed.')
        return redirect('universities:university_list')
    return render(request, 'applications/confirm_delete.html', {'obj': uni})

@login_required
def university_detail(request, pk):
    uni = get_object_or_404(University, pk=pk, user=request.user)

    if uni.id == 7:
        uni.tasks.all().delete()
    if not uni.tasks.exists():
        from .models import generate_tasks_for_university
        generate_tasks_for_university(uni)

    tasks = uni.tasks.all().order_by('order', 'created_at')
    today = timezone.now().date()
    task_form = ApplicationTaskForm()

    return render(request, 'applications/university_detail.html', {
        'uni': uni,
        'tasks': tasks,
        'task_total_count': tasks.count(),
        'task_done_count': tasks.filter(status='done').count(),
        'task_form': task_form,
        'today': today,
    })

@login_required
def scholarship_list(request):
    scholarships = Scholarship.objects.filter(university__user=request.user).select_related('university')
    return render(request, 'applications/scholarship_list.html', {'scholarships': scholarships})

@login_required
def scholarship_create(request, uni_pk):
    uni = get_object_or_404(University, pk=uni_pk, user=request.user)
    form = ScholarshipForm(request.POST or None)
    if form.is_valid():
        s = form.save(commit=False)
        s.university = uni
        s.save()
        messages.success(request, 'Scholarship added.')
        return redirect('universities:university_detail', pk=uni_pk)
    return render(request, 'applications/scholarship_form.html', {'form': form, 'uni': uni})

@login_required
def documents(request):
    docs = Document.objects.filter(user=request.user).order_by('-uploaded_at')
    form = DocumentForm(request.user, request.POST or None, request.FILES or None)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.user = request.user
        doc.save()
        messages.success(request, 'Document uploaded.')
        return redirect('universities:documents')
    return render(request, 'applications/documents.html', {'docs': docs, 'form': form})

@login_required
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk, user=request.user)
    if request.method == 'POST':
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Document removed.')
    return redirect('universities:documents')

@login_required
def scores_view(request):
    try:
        scores = request.user.test_scores
    except TestScore.DoesNotExist:
        scores = None
    form = TestScoreForm(request.POST or None, instance=scores)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        messages.success(request, 'Scores saved.')
        return redirect('universities:scores')
    return render(request, 'applications/scores.html', {'form': form, 'scores': scores})

@require_POST
@login_required
def task_toggle(request, pk):
    task = get_object_or_404(ApplicationTask, pk=pk, university__user=request.user)
    cycle = {'pending': 'done', 'done': 'pending', 'in_progress': 'done'}
    task.status = cycle.get(task.status, 'pending')
    task.save(update_fields=['status', 'updated_at'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': task.status})
    return redirect('universities:university_detail', pk=task.university_id)

@require_POST
@login_required
def task_update(request, pk):
    """
    Update a single task's title, notes, due_date, or status via a small form
    embedded in university_detail.
    POST /universities/tasks/<pk>/update/
    """
    task = get_object_or_404(ApplicationTask, pk=pk, university__user=request.user)
    form = ApplicationTaskForm(request.POST, instance=task)
    if form.is_valid():
        form.save()
        messages.success(request, 'Task updated.')
    return redirect('universities:university_detail', pk=task.university_id)

@require_POST
@login_required
def task_delete(request, pk):
    """
    Delete a task.
    POST /universities/tasks/<pk>/delete/
    """
    task = get_object_or_404(ApplicationTask, pk=pk, university__user=request.user)
    uni_pk = task.university_id
    task.delete()
    messages.success(request, 'Task removed.')
    return redirect('universities:university_detail', pk=uni_pk)

@require_POST
@login_required
def task_create(request, uni_pk):
    uni = get_object_or_404(University, pk=uni_pk, user=request.user)
    form = ApplicationTaskForm(request.POST)
    if form.is_valid():
        task = form.save(commit=False)
        task.university = uni
        task.save()
        messages.success(request, 'Task added.')
    else:
        messages.error(request, f'Error: {form.errors}')
    return redirect('universities:university_detail', pk=uni_pk)

@require_POST
@login_required
def task_regenerate(request, uni_pk):
    """
    Re-generate the default checklist for a university (only adds missing tasks,
    never deletes existing ones — safe to call at any time).
    POST /universities/<uni_pk>/tasks/regenerate/
    """
    uni = get_object_or_404(University, pk=uni_pk, user=request.user)
    # Temporarily clear tasks so generate_tasks_for_university will run
    # Only delete tasks that are still 'pending' and were auto-generated
    # (title matches a template title) — leaves custom / in-progress tasks alone.
    from .models import TASK_TEMPLATES, generate_tasks_for_university
    template_titles = {title for _, _, title in TASK_TEMPLATES.get(uni.university_type, [])}
    uni.tasks.filter(status='pending', title__in=template_titles).delete()
    generate_tasks_for_university(uni)
    messages.success(request, 'Checklist refreshed.')
    return redirect('universities:university_detail', pk=uni_pk)

@login_required
def document_version_upload(request, doc_pk):
    doc  = get_object_or_404(Document, pk=doc_pk, user=request.user)
    form = DocumentVersionForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        v = form.save(commit=False)
        v.document    = doc
        v.uploaded_by = request.user
        v.save()
        messages.success(request, f'"{v.label}" uploaded.')
        return redirect('universities:document_detail', pk=doc_pk)
    return render(request, 'applications/document_version_upload.html', {
        'form': form, 'doc': doc,
    })

@login_required
def document_version_delete(request, pk):
    version = get_object_or_404(DocumentVersion, pk=pk, document__user=request.user)
    doc_pk  = version.document_id
    if request.method == 'POST':
        version.file.delete(save=False)
        version.delete()
        messages.success(request, 'Version removed.')
    return redirect('universities:document_detail', pk=doc_pk)

@login_required
def document_detail(request, pk):
    doc      = get_object_or_404(Document, pk=pk, user=request.user)
    versions = doc.versions.order_by('uploaded_at')
    links    = doc.share_links.filter(is_active=True).order_by('-created_at')
    version_form = DocumentVersionForm()
    return render(request, 'applications/document_detail.html', {
        'doc': doc, 'versions': versions,
        'links': links, 'version_form': version_form,
    })

@login_required
@require_POST
def share_link_create(request, doc_pk):
    doc = get_object_or_404(Document, pk=doc_pk, user=request.user)
    days = int(request.POST.get('days', 7))
    days = max(1, min(days, 30))           
    link = ShareLink.objects.create(
        document   = doc,
        expires_at = timezone.now() + timezone.timedelta(days=days),
    )
    messages.success(request, f'Share link created — expires in {days} day(s).')
    return redirect('universities:document_detail', pk=doc_pk)

@login_required
@require_POST
def share_link_revoke(request, pk):
    link = get_object_or_404(ShareLink, pk=pk, document__user=request.user)
    link.is_active = False
    link.save(update_fields=['is_active'])
    messages.success(request, 'Share link revoked.')
    return redirect('universities:document_detail', pk=link.document_id)

def shared_document_view(request, token):
    link = get_object_or_404(ShareLink, token=token)

    if not link.is_valid:
        return render(request, 'applications/share_expired.html', status=410)

    link.accessed_count += 1
    link.save(update_fields=['accessed_count'])

    latest = link.document.versions.order_by('-uploaded_at').first()
    file_field = latest.file if latest else link.document.file

    response = FileResponse(file_field.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_field.name)}"'
    return response

@login_required
def calendar_feed_info(request):
    """Shows the user their calendar subscription URL and lets them regenerate it."""
    token = CalendarToken.get_or_create_for(request.user)
    url   = request.build_absolute_uri(f'/calendar/{token.token}.ics')
    return render(request, 'applications/calendar_feed.html', {
        'token': token, 'feed_url': url,
    })

@login_required
@require_POST
def calendar_token_regenerate(request):
    token = CalendarToken.get_or_create_for(request.user)
    token.token = _uuid.uuid4()
    token.save(update_fields=['token'])
    messages.success(request, 'Calendar URL regenerated. Update the link in your calendar app.')
    return redirect('universities:calendar_feed_info')

def ical_feed(request, token):
    """Public iCal endpoint — no login needed, protected by the UUID token."""
    cal_token = get_object_or_404(CalendarToken, token=token)
    user      = cal_token.user

    universities = University.objects.filter(
        user=user,
        deadline__isnull=False,
    ).exclude(status__in=['rejected'])

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//UniTracker//Application Deadlines//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{user.username} — UniTracker Deadlines',
        'X-WR-TIMEZONE:UTC',
    ]

    for uni in universities:
        uid      = f"unitracker-{uni.pk}@unitracker"
        dtstart  = uni.deadline.strftime('%Y%m%d')
        dtstamp  = timezone.now().strftime('%Y%m%dT%H%M%SZ')
        summary  = _ical_escape(f"{uni.name} — {uni.program} deadline")
        desc     = _ical_escape(
            f"Status: {uni.get_status_display()} | Type: {uni.get_university_type_display()} | {uni.country}"
        )
        url_val  = uni.website or ''

        lines += [
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{dtstamp}',
            f'DTSTART;VALUE=DATE:{dtstart}',
            f'DTEND;VALUE=DATE:{dtstart}',
            f'SUMMARY:{summary}',
            f'DESCRIPTION:{desc}',
            f'URL:{url_val}',
            f'STATUS:{"CONFIRMED" if uni.status not in ["rejected","deferred"] else "CANCELLED"}',
            'END:VEVENT',
        ]

    lines.append('END:VCALENDAR')

    content = '\r\n'.join(lines) + '\r\n'
    return HttpResponse(content, content_type='text/calendar; charset=utf-8')

def _ical_escape(text):
    """Escape special characters per RFC 5545."""
    return text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
