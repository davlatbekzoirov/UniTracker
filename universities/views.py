from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q, Case, When, Value, CharField
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import University, Scholarship, Document, TestScore, ApplicationTask, generate_tasks_for_university
from .forms  import RegisterForm, UniversityForm, ScholarshipForm, DocumentForm, TestScoreForm, ApplicationTaskForm

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome, {user.username}!')
        return redirect('dashboard')
    return render(request, 'applications/auth.html', {'form': form, 'mode': 'register'})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    if form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(request.GET.get('next', 'dashboard'))
    return render(request, 'applications/auth.html', {'form': form, 'mode': 'login'})


def logout_view(request):
    logout(request)
    return redirect('login')


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
        
    return render(request, 'applications/dashboard.html', {
        'universities': universities, 'upcoming': upcoming,
        'stats': stats, 'scores': scores,
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
        return redirect('university_list')
    return render(request, 'applications/university_form.html', {'form': form, 'action': 'Add'})


@login_required
def university_edit(request, pk):
    uni = get_object_or_404(University, pk=pk, user=request.user)
    form = UniversityForm(request.POST or None, instance=uni)
    if form.is_valid():
        form.save()
        messages.success(request, 'Updated.')
        return redirect('university_list')
    return render(request, 'applications/university_form.html', {
        'form': form, 'action': 'Edit', 'uni': uni,
    })


@login_required
def university_delete(request, pk):
    uni = get_object_or_404(University, pk=pk, user=request.user)
    if request.method == 'POST':
        uni.delete()
        messages.success(request, f'{uni.name} removed.')
        return redirect('university_list')
    return render(request, 'applications/confirm_delete.html', {'obj': uni})


@login_required
def university_detail(request, pk):
    uni = get_object_or_404(University, pk=pk, user=request.user)

    # DELETE THESE LINES:
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
        return redirect('university_detail', pk=uni_pk)
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
        return redirect('documents')
    return render(request, 'applications/documents.html', {'docs': docs, 'form': form})


@login_required
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk, user=request.user)
    if request.method == 'POST':
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Document removed.')
    return redirect('documents')


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
        return redirect('scores')
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
    return redirect('university_detail', pk=task.university_id)

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
    return redirect('university_detail', pk=task.university_id)

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
    return redirect('university_detail', pk=uni_pk)


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
    return redirect('university_detail', pk=uni_pk)


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
    return redirect('university_detail', pk=uni_pk)
