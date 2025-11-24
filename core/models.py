import json
from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string
from django.core.exceptions import ValidationError

class User(AbstractUser):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    email = models.EmailField(unique=True)

    def clean(self):
        if self.username == self.email:
            raise ValidationError('Username and email cannot be the same.')

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=6, unique=True, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Enrollment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subject', 'student')

class Question(models.Model):
    LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True)
    topic = models.CharField(max_length=100)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES,default='medium')
    question = models.CharField(max_length=100)
    hint = models.TextField(blank=True)
    

    def __str__(self):
        return f"{self.topic} - {self.question[:50]}"

class Assignment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    topic = models.CharField(max_length=100)  # From CSV topics
    description = models.TextField()
    announcement_date = models.DateTimeField()
    due_date = models.DateTimeField()
    pdf_file = models.FileField(upload_to='assignments/', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_adaptive = models.BooleanField(default=False)  
    questions = models.ManyToManyField(Question, blank=True)
    students = models.ManyToManyField(User, related_name='assignments', blank=True, help_text="Students assigned to this assignment")
    def __str__(self):
        return f"{self.subject.name} - {self.topic}"

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    answers = models.TextField()  # JSON-like or plain text for answers
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(null=True, blank=True)  # Out of 100
    feedback = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.assignment}"
    
    def has_real_answers(self):
        """Returns True if answers has non-empty content."""
        if not self.answers:
            return False
        try:
            parsed = json.loads(self.answers)
            if isinstance(parsed, dict):
                return any(
                    value and str(value).strip()  # Non-empty strings/keys
                    for value in parsed.values()
                )
            elif isinstance(parsed, list):
                return any(str(item).strip() for item in parsed)
            return bool(parsed)
        except (json.JSONDecodeError, TypeError):
            return False

    def is_submitted(self):
        """True if submitted_at is set AND has real answers."""
        return self.submitted_at and self.has_real_answers()