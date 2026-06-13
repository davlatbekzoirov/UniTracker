from django.urls import path
from . import views
from .autocomplete import university_autocomplete

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

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

    path('documents/<int:pk>/',                    views.document_detail,          name='document_detail'),
    path('documents/<int:doc_pk>/versions/add/',   views.document_version_upload,  name='document_version_upload'),
    path('documents/versions/<int:pk>/delete/',    views.document_version_delete,  name='document_version_delete'),
    path('documents/<int:doc_pk>/share/',          views.share_link_create,        name='share_link_create'),
    path('documents/share/<int:pk>/revoke/',       views.share_link_revoke,        name='share_link_revoke'),
    path('shared/<uuid:token>/',                   views.shared_document_view,     name='shared_document'),

    path('calendar/', views.calendar_feed_info, name='calendar_feed_info'),
    path('calendar/regenerate/', views.calendar_token_regenerate, name='calendar_token_regenerate'),
    path('calendar/<uuid:token>.ics', views.ical_feed, name='ical_feed'),
]