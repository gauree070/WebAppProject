from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Subject, Assignment, Enrollment, Submission, Question
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, get_user_model

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, widget=forms.Select())

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Passwords do not match.')
        return cleaned_data

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Username or Email')

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if not username or not password:
            raise forms.ValidationError('Please enter both username/email and password.')

        # Email-based login
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                user = authenticate(self.request, username=user.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(self.request, username=username, password=password)

        if user is None:
            raise forms.ValidationError('Invalid login credentials.')

        if not user.is_active:
            raise forms.ValidationError('This account is inactive.')

        self.confirm_login_allowed(user)
        self.user_cache = user
        return self.cleaned_data

    def get_user(self):
        return self.user_cache
class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']

from django import forms
from django.core.exceptions import ValidationError

class AssignmentForm(forms.Form):
    topic = forms.ChoiceField(
        choices=[],
        label='Topic',
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    questions = forms.ChoiceField(
        choices=[],
        label='Select One Question for this Assignment',
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    description = forms.CharField(
        label='Description',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    announcement_date = forms.DateTimeField(
        label='Announcement Date',
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=True
    )
    due_date = forms.DateTimeField(
        label='Due Date',
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=True
    )
    pdf_file = forms.FileField(
        label='PDF File (Optional)',
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        self.questions_choices = kwargs.pop('questions_choices', [])  # Pass from view
        super().__init__(*args, **kwargs)
        self.fields['questions'].choices = self.questions_choices

    def clean(self):
        cleaned_data = super().clean()
        topic = cleaned_data.get('topic')
        questions = cleaned_data.get('questions')
        if topic and not questions:
            raise ValidationError({'questions': 'Please select a question for the chosen topic.'})
        return cleaned_data
    
class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['answers']
        widgets = {
            'answers': forms.Textarea(attrs={'rows': 10, 'placeholder': 'Enter your answers here (e.g., Q1: ..., Q2: ...)'}),
        }

class EnrollmentForm(forms.ModelForm):
    code = forms.CharField(label='Subject Code', max_length=6)

    class Meta:
        model = Enrollment
        fields = ['code']