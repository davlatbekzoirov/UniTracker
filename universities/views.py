from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import University, Scholarship, Document, TestScore
from .forms import RegisterForm, UniversityForm, ScholarshipForm, DocumentForm, TestScoreForm


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
    stats = {
        'total': universities.count(),
        'submitted': universities.filter(status__in=['submitted','interview','accepted','deferred']).count(),
        'accepted': universities.filter(status='accepted').count(),
        'interview': universities.filter(status='interview').count(),
        'due_soon': universities.filter(deadline__gte=today, deadline__lte=today + timezone.timedelta(days=30)).count(),
        'reach': universities.filter(university_type='reach').count(),
        'match': universities.filter(university_type='match').count(),
        'safety': universities.filter(university_type='safety').count(),
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
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    q = request.GET.get('q', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if type_filter:
        qs = qs.filter(university_type=type_filter)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(country__icontains=q) | Q(program__icontains=q))
    return render(request, 'applications/university_list.html', {
        'universities': qs, 'status_filter': status_filter,
        'type_filter': type_filter, 'q': q,
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
    return render(request, 'applications/university_detail.html', {'uni': uni})


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
