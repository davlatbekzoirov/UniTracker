from django.urls import path
from . import views
from .autocomplete import university_autocomplete

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('universities/', views.university_list, name='university_list'),
    path('universities/add/', views.university_create, name='university_create'),
    path('universities/<int:pk>/', views.university_detail, name='university_detail'),
    path('universities/<int:pk>/edit/', views.university_edit, name='university_edit'),
    path('universities/<int:pk>/delete/', views.university_delete, name='university_delete'),
    path('universities/<int:uni_pk>/scholarships/add/', views.scholarship_create, name='scholarship_create'),

    path('universities/<int:uni_pk>/tasks/add/', views.task_create, name='task_create'),
    path('universities/<int:uni_pk>/tasks/regenerate/', views.task_regenerate, name='task_regenerate'),
    path('tasks/<int:pk>/toggle/', views.task_toggle, name='task_toggle'),
    path('tasks/<int:pk>/update/', views.task_update, name='task_update'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),

    path('scholarships/', views.scholarship_list, name='scholarship_list'),
    path('documents/', views.documents, name='documents'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
    path('scores/', views.scores_view, name='scores'),

    path('autocomplete/', university_autocomplete, name='university_autocomplete'),
]