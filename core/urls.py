from django.urls import include, path
from . import views
from django.contrib.auth import logout  
from django.shortcuts import redirect
app_name = 'core'


urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', lambda request: (logout(request), redirect('home')), name='logout'),  # Add from django.contrib.auth
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/create-subject/', views.create_subject, name='create_subject'),
    path('teacher/create-assignment/<int:subject_id>/', views.create_assignment, name='create_assignment'),
    path('teacher/grade/<int:submission_id>/', views.grade_submission, name='grade_submission'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/enroll/', views.enroll_subject, name='enroll_subject'),
    path('student/submit/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
    path('load-questions/<int:subject_id>/', views.load_questions, name='load_questions'),
    path('teacher/delete-assignment/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),
    path('submit/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
    path('student/delete-submission/<int:submission_id>/', views.delete_submission, name='delete_submission'),
    path('delete-submission/<int:submission_id>/', views.delete_submission, name='delete_submission'),
    path('student/subject/<int:subject_id>/', views.subject_detail, name='subject_detail'), 
    path('teacher/subject/<int:subject_id>/', views.teacher_subject_detail, name='teacher_subject_detail'),
    path('teacher/delete-subject/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    
]

