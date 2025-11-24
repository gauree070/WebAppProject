import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q
from .forms import CustomUserCreationForm, CustomAuthenticationForm, SubjectForm, AssignmentForm, SubmissionForm, EnrollmentForm
from .models import User, Subject, Enrollment, Question, Assignment, Submission
import csv
import os
from django.conf import settings
from datetime import datetime, timedelta
from django.contrib.auth import logout  
from django.views.decorators.http import require_http_methods
from django.views.generic.edit import DeleteView
from django.utils import timezone
import json
from django.core.exceptions import ObjectDoesNotExist


def home(request):
    return render(request, 'core/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            role = form.cleaned_data['role']
            if role == 'teacher':
                return redirect('core:teacher_dashboard')
            else:
                return redirect('core:student_dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                if user.is_active:
                    login(request, user)
                    if user.role == 'teacher':
                        return redirect('core:teacher_dashboard')

                    else:
                        return redirect('core:student_dashboard')
                else:
                    messages.error(request, "Your account is inactive.")
            else:
                messages.error(request, "Invalid login credentials.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomAuthenticationForm()

    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def teacher_dashboard(request):
    # Fixed: Use 'teacher' (singular ForeignKey) instead of 'teachers' (non-existent ManyToMany)
    subjects = Subject.objects.filter(teacher=request.user).order_by('name')
    
    # Assignments created by this teacher
    assignments = Assignment.objects.filter(
        created_by=request.user
    ).prefetch_related('questions').order_by('due_date')  # Added order_by for better UX

    # Preview logic (your existing code, unchanged)
    for ass in assignments:
        questions = getattr(ass, 'questions', None)
        if questions and questions.exists():
            first_q = questions.first()
            ass.display_question = f"{first_q.question[:50]}..." if first_q.question else "No question"
            ass.display_hint = first_q.hint or ""
        else:
            ass.display_question = "No question available"
            ass.display_hint = ""

    # Submissions for teacher's assignments
    submissions = Submission.objects.filter(
        assignment__created_by=request.user
    ).select_related('assignment', 'student').order_by('-submitted_at')  # Added select_related and order_by for efficiency/UX

    return render(request, 'core/teacher_dashboard.html', {
        'subjects': subjects,
        'assignments': assignments,
        'submissions': submissions,
    })

@login_required
def create_subject(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.teacher = request.user
            subject.save()
            messages.success(request, 'Subject created successfully!')
            return redirect('core:teacher_dashboard')
    else:
        form = SubjectForm()
    return render(request, 'core/create_subject.html', {'form': form})

@login_required
def create_assignment(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    # Load CSV questions for this subject
    questions_by_topic, topics = load_csv_data(subject.name)

    topic_choices = [('', '-- Select a Topic --')] + [(t, t) for t in topics]

    selected_topic = request.GET.get('topic', '')
    show_question_div = bool(selected_topic and selected_topic in questions_by_topic)

    # Build question choices (indexed)
    questions_data = []
    question_choices = []

    if show_question_div:
        questions_data = questions_by_topic[selected_topic]
        for idx, q in enumerate(questions_data):
            label = f"{q['level'].title()}: {q['question']} (Hint: {q['hint']})"
            question_choices.append((str(idx), label))

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        form.fields['topic'].choices = topic_choices
        form.fields['questions'].choices = question_choices

        if form.is_valid():

            topic = form.cleaned_data['topic']
            selected_indices = form.cleaned_data.get('questions', [])

            # Convert selected indices → actual question dicts
            selected_questions = [
                questions_data[int(i)] for i in selected_indices
            ] if selected_indices else []

            # 1️⃣ Create Assignment
            assignment = Assignment.objects.create(
                subject=subject,
                topic=topic,
                description=form.cleaned_data['description'],
                announcement_date=form.cleaned_data['announcement_date'],
                due_date=form.cleaned_data['due_date'],
                pdf_file=form.cleaned_data.get('pdf_file'),
                created_by=request.user,
                is_adaptive=True
            )

            # 2️⃣ Save Questions into DB + add to assignment
            for q in selected_questions:
                q_obj, _ = Question.objects.get_or_create(
                    subject=subject,
                    topic=topic,
                    level=q['level'],
                    question=q['question'],
                    hint=q['hint']
                )
                assignment.questions.add(q_obj)

            messages.success(
                request,
                f'Assignment created for {topic} in {subject.name}! ({len(selected_questions)} questions)'
            )

            return redirect('core:teacher_subject_detail', subject_id=subject.id)

        else:
            print("DEBUG: Form errors:", form.errors)

    else:
        form = AssignmentForm(initial={'topic': selected_topic})
        form.fields['topic'].choices = topic_choices
        form.fields['questions'].choices = question_choices

    context = {
        'form': form,
        'show_question_div': show_question_div,
        'subject': subject,
    }
    return render(request, 'core/create_assignment.html', context)


import json
import random
from datetime import timedelta
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from core.models import Submission, Assignment, Question  # Add User if needed

@login_required
def grade_submission(request, submission_id):
    submission = get_object_or_404(
        Submission,
        id=submission_id,
        assignment__created_by=request.user
    )
    
    assignment = submission.assignment
    
    if request.method == 'POST':
        score_input = request.POST.get('score', '')
        feedback = request.POST.get('feedback', '').strip()
        
        try:
            if score_input:
                score_value = float(score_input)
                submission.score = max(0, min(10, int(score_value)))
            else:
                submission.score = None
        except ValueError:
            messages.error(request, 'Invalid score. Enter a number between 0-10.')
        else:
            submission.feedback = feedback
            submission.graded_at = timezone.now()
            submission.save()
            messages.success(request, f'Graded {submission.student.username}\'s submission: {submission.score}/10')
            
            if submission.score is not None:
                # Level based on score (low <4, medium 4-6, high 7+)
                if submission.score < 4:
                    level = 'low'
                elif submission.score < 7:
                    level = 'medium'
                else:
                    level = 'high'
                
                # Specific dupe check: Per topic + level + student (no block if new level)
                existing_adaptive = Assignment.objects.filter(
                    topic__iexact=submission.assignment.topic,
                    description__icontains=f"Level: {level}",
                    is_adaptive=True,
                    students=submission.student  # NEW: Student-specific
                ).exists()
                
                if not existing_adaptive:  # Create if no match
                    adaptive_questions = Question.objects.filter(
                        topic__iexact=submission.assignment.topic,
                        level__iexact=level
                    )
                    
                    if adaptive_questions.exists():
                        adaptive_question = random.choice(list(adaptive_questions))
                        
                        adaptive_assignment = Assignment.objects.create(
                            subject=submission.assignment.subject,
                            topic=submission.assignment.topic,
                            description=f"Adaptive follow-up on {submission.assignment.topic} (Level: {level})",
                            announcement_date=timezone.now(),
                            due_date=timezone.now() + timedelta(days=7),
                            created_by=request.user,
                            is_adaptive=True,
                        )
                        adaptive_assignment.questions.add(adaptive_question)
                        
                        # NEW: Assign to student & auto-pending submission
                        adaptive_assignment.students.add(submission.student)
                       
                        
                        messages.success(request, f'Adaptive {level}-level question assigned to {submission.student.username}!')
                    else:
                        messages.warning(request, f'No {level}-level questions for {submission.assignment.topic}.')
                else:
                    messages.info(request, f'Low-level adaptive already assigned to {submission.student.username}.')
        
        if submission.score is not None:
            return redirect('core:teacher_subject_detail', subject_id=submission.assignment.subject.id)
    
    # GET context (unchanged)
    try:
        parsed_answers = json.loads(submission.answers) if submission.answers else {}
    except json.JSONDecodeError:
        parsed_answers = {'Error': 'Invalid answers format'}
    
    context = {
        'submission': submission,
        'assignment': assignment,
        'student_name': submission.student.get_full_name() or submission.student.username,
        'parsed_answers': parsed_answers,
        'max_score': 10,
    }
    return render(request, 'core/grade_submission.html', context)

@login_required
def student_dashboard(request):
    enrollments = Enrollment.objects.filter(student=request.user).select_related('subject')
    available_assignments = Assignment.objects.filter(
        subject__in=enrollments.values('subject'),
        due_date__gt=timezone.now(),  # Fixed: Use timezone.now()
    ).select_related('subject').prefetch_related('questions')

    for ass in available_assignments:
        questions = getattr(ass, 'questions', None)
        if questions and questions.exists():
            first_q = questions.first()
            ass.display_question = f"{first_q.question[:50]}..." if first_q.question else "No question"
            ass.display_hint = first_q.hint or ""
        else:
            ass.display_question = "No question available"
            ass.display_hint = ""

    submissions = Submission.objects.filter(student=request.user)
    return render(request, 'core/student_dashboard.html', {
        'enrollments': enrollments,
        'available_assignments': available_assignments,
        'submissions': submissions,
    })

@login_required
def enroll_subject(request):
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                subject = Subject.objects.get(code=code)
                Enrollment.objects.get_or_create(subject=subject, student=request.user)
                messages.success(request, 'Enrolled successfully!')
            except Subject.DoesNotExist:
                messages.error(request, 'Invalid code.')
        return redirect('core:student_dashboard')
    else:
        form = EnrollmentForm()
    return render(request, 'core/enroll_subject.html', {'form': form})





@login_required
def submit_assignment(request, assignment_id):
    # Secure access: Ensure student is enrolled in the subject
    assignment = get_object_or_404(
        Assignment,
        id=assignment_id,
        subject__enrollment__student=request.user
    )
    
    # Check if already submitted
    submission = Submission.objects.filter(
        student=request.user, 
        assignment=assignment
    ).first()
    is_submitted = submission is not None
    print(f"DEBUG: Already submitted? {is_submitted}")

    # Get questions (teacher-selected or fallback)
    selected_questions = list(assignment.questions.all())
    if not selected_questions:
        selected_questions = list(Question.objects.filter(topic=assignment.topic))
        if selected_questions:
            messages.warning(request, f"No questions linked to this assignment. Showing topic-based fallback for '{assignment.topic}'.")
            no_questions = False
        else:
            messages.error(request, 'No questions available for this assignment.')
            no_questions = True
            due_date_passed = assignment.due_date < timezone.now() if hasattr(assignment, 'due_date') else False
            context = {
                'assignment': assignment,
                'selected_questions': [],  # Empty list
                'no_questions': True,
                'due_date_passed': due_date_passed,
                'is_submitted': False,
                'submission': None,
            }
            return render(request, 'core/submit_assignment.html', context)
    else:
        no_questions = False
    
    due_date_passed = assignment.due_date < timezone.now() if hasattr(assignment, 'due_date') else False
    
    # Parse answers for template if submitted (or from POST)
    answers_dict = {}
    if submission and submission.answers:
        try:
            answers_dict = json.loads(submission.answers)
        except json.JSONDecodeError:
            answers_dict = {}
    
    if request.method == 'POST' and not is_submitted:
        # Manually collect answers dict {q_id: answer_text}
        print("DEBUG: POST processing started")
        answers_dict = {}
        for q in selected_questions:
            answer_key = f'answers_{q.id}'
            raw_answer = request.POST.get(answer_key, '').strip()  
            answers_dict[str(q.id)] = raw_answer
            print(f"DEBUG: Q {q.id} key: '{answer_key}', Raw: '{raw_answer}' (len: {len(raw_answer)})")

        # Save if ANY answer has content (non-empty after trim)
        if any(answers_dict.values()):  # At least one non-empty
            submission = Submission.objects.create(
                assignment=assignment,
                student=request.user,
                answers=json.dumps(answers_dict),  # Save as JSON string
                submitted_at=timezone.now()
            )
            print(f"DEBUG: Forced save! ID: {submission.id}, Dict: {answers_dict}")
           
            is_submitted = True  # Update flag
            # RELOAD submission for fresh data
            submission = Submission.objects.filter(
                student=request.user, 
                assignment=assignment
            ).first()
            
            # Re-parse answers_dict from new submission
            if submission and submission.answers:
                try:
                    answers_dict = json.loads(submission.answers)
                except json.JSONDecodeError:
                    answers_dict = {}
        #else:
        #   messages.warning(request, 'No answers provided. Submission not saved.')
    
    # Attach answer to each question object for template (temporary, per-request)
    for q in selected_questions:
        q.answer = answers_dict.get(str(q.id), request.POST.get(f'answers_{q.id}', '').strip() if request.method == 'POST' else '')
    
    context = {
        'assignment': assignment,
        'selected_questions': selected_questions,  # Now with .answer attached
        'no_questions': no_questions,
        'due_date_passed': due_date_passed,
        'is_submitted': is_submitted,
        'submission': submission,
    }
    return render(request, 'core/submit_assignment.html', context)

@require_http_methods(["GET"])
def load_questions(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)
    topic = request.GET.get('topic')
    if not topic:
        return JsonResponse({'success': False, 'error': 'No topic provided'})
    filtered_questions = Question.objects.filter(subject=subject, topic=topic)
    choices = []  
    for q in filtered_questions:
        choices.append({
            'value': q.id,
            'label': q.question[:60] + '...' if len(q.question) > 60 else q.question  
        })
    
    return JsonResponse({
        'success': True,
        'choices': [{'value': val, 'label': label} for val, label in choices]
    })


@login_required
def delete_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, created_by=request.user)

    if request.method == 'POST':
        submission_count = Submission.objects.filter(assignment=assignment).count()
        assignment.delete()
        messages.success(request, f'Assignment "{assignment.topic}" deleted! ({submission_count} submissions removed.)')
        return redirect('core:teacher_subject_detail', subject_id=assignment.subject.id)  

    return render(request, 'core/confirm_delete_submission.html', {
        'assignment': assignment
    })


@login_required
def delete_submission(request, submission_id):
    try:
        # Keep your secure query—same as before
        submission = Submission.objects.get(
            id=submission_id, 
            student=request.user
        )
    except ObjectDoesNotExist:
        # Graceful handling: Inform user without revealing details
        messages.error(request, "The submission you're trying to delete wasn't found. It may have already been removed or doesn't belong to you.")
        # Redirect to a safe fallback (adjust URL name as needed, e.g., your submissions list or dashboard)
        return redirect('core:student_dashboard')  # Or 'core:your_submissions_list'—pick one that exists
    
    if request.method == 'POST':
        assignment_title = submission.assignment.topic
        submission.delete()
        messages.success(request, f'Submission for "{assignment_title}" deleted successfully.')
        return redirect('core:subject_detail', subject_id=submission.assignment.subject.id)
    
    # GET: Render confirmation page
    return render(request, 'core/confirm_delete_submission.html', {
        'submission': submission,
        'assignment_title': submission.assignment.topic,
    })

@login_required
def subject_detail(request, subject_id):
    # Secure: Ensure user is enrolled in this subject
    enrollment = get_object_or_404(Enrollment, student=request.user, subject_id=subject_id)
    subject = enrollment.subject

    # Available assignments for this subject
    available_assignments = Assignment.objects.filter(
        subject=subject,
        due_date__gt=timezone.now(),
    ).select_related('subject').prefetch_related('questions').order_by('due_date')

    # Preview logic
    for ass in available_assignments:
        questions = getattr(ass, 'questions', None)
        if questions and questions.exists():
            first_q = questions.first()
            ass.display_question = f"{first_q.question[:500]}" if first_q.question else "No question"
            ass.display_hint = first_q.hint or ""
        else:
            ass.display_question = "No question available"
            ass.display_hint = ""

    # Submitted assignments for this subject
    submissions = Submission.objects.filter(
        student=request.user,
        assignment__subject=subject
    ).select_related('assignment').order_by('-submitted_at')

    return render(request, 'core/subject_detail.html', {
        'subject': subject,
        'available_assignments': available_assignments,
        'submissions': submissions,
        'enrollment': enrollment,  # Optional, for back link
    })



@login_required
def teacher_subject_detail(request, subject_id):
    # Fixed: Use 'teacher' (singular ForeignKey) for security check
    subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)

    # Generated Assignments for this subject
    assignments = Assignment.objects.filter(
        subject=subject
    ).select_related('subject').prefetch_related('questions').order_by('due_date')

    # Preview logic (adapted from your dashboard)
    for ass in assignments:
        questions = getattr(ass, 'questions', None)
        if questions and questions.exists():
            first_q = questions.first()
            ass.display_question = f"{first_q.question[:50]}..." if first_q.question else "No question"
            ass.display_hint = first_q.hint or ""
        else:
            ass.display_question = "No question available"
            ass.display_hint = ""

    # Submissions for this subject's assignments
    submissions = Submission.objects.filter(
        assignment__subject=subject
    ).select_related('assignment', 'student').order_by('-submitted_at')

    return render(request, 'core/teacher_subject_detail.html', {
        'subject': subject,
        'assignments': assignments,
        'submissions': submissions,
    })

@login_required
def delete_subject(request, subject_id):
    # Secure: Fetch only if owned by current teacher
    subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)
    
    if request.method == 'POST':
        subject_name = subject.name  # For message
        subject.delete()
        messages.success(request, f'Subject "{subject_name}" deleted successfully.')
        return redirect('core:teacher_dashboard')  # Assumes namespace; adjust if not
    
    # GET: Optional confirmation page (or use JS in template for inline)
    return render(request, 'core/confirm_delete_subject.html', {
        'subject': subject,
    })



def load_csv_data(subject_name):
    questions_by_topic = {}
    csv_path = 'questions.csv'  # Place next to manage.py
    full_path = os.path.join(settings.BASE_DIR, csv_path)
    
    print(f"DEBUG: Filtering CSV for subject '{subject_name}' from {full_path}")  # Check console
    
    if not os.path.exists(full_path):
        print("DEBUG: CSV not found - create 'questions.csv' in project root")
        return {}, []
    
    try:
        with open(full_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                subj = row.get('subject', '').strip()
                if subj == subject_name:  # Filter by current subject
                    topic = row.get('topic', '').strip()
                    if topic:
                        if topic not in questions_by_topic:
                            questions_by_topic[topic] = []
                        questions_by_topic[topic].append({
                            'level': row.get('level', 'low').strip().lower(),
                            'question': row.get('question', '').strip(),
                            'hint': row.get('hint', '').strip()
                        })
        print(f"DEBUG: Filtered topics for '{subject_name}': {sorted(questions_by_topic.keys())}")
    except Exception as e:
        print(f"DEBUG: CSV error: {e}")
    
    topics = sorted(questions_by_topic.keys())
    return questions_by_topic, topics

