Edu Platform
A lightweight Learning Management System (LMS) built with Django and Python, designed for programming education. Teachers create adaptive assignments from CSV questions, students submit code, and the system auto-generates follow-up challenges based on performance scores.
Django Python License: MIT
🚀 Overview
Edu Platform simplifies teaching computer programming topics like control statements and loops. It supports role-based access (teachers/students), CSV-driven question banks with difficulty levels (low/medium/high), and basic adaptive learning—low scores trigger easier remedial assignments. Built for quick setup, it's ideal for classrooms or self-paced coding bootcamps.
Key inspirations: Moodle's simplicity meets Duolingo's adaptivity, but focused on code submissions and manual grading with ML-ready hooks.
✨ Features

Role-Based Dashboards: Teachers manage subjects/assignments; students view/submit work.
Question Management: Load questions from CSV (topic, difficulty, text, hint). Generate mixed-level assignments.
Code Submissions: Students submit answers as JSON (e.g., {"q1": "print('Hello')"}); teachers grade 0-10 with feedback.
Adaptive Assignments: Auto-create follow-ups based on scores (<4: low, 4-6: medium, 7+: high). Deduped per student/topic.
Clean UI: Bootstrap tables for submissions (filtered for real answers only—no phantom "Pending" rows).
Performance Optimized: Eager loading (select_related/prefetch_related), Debug Toolbar integration.
Extensible: Hooks for basic ML (e.g., scikit-learn auto-grading) and future features like auto-tests.

📸 Screenshots

Teacher Dashboard: Overview of subjects, recent submissions, and unsubmitted adaptives.Teacher Dashboard(Add your screenshot here)
Student Assignment View: Questions, hints, and submission form.Student Assignment
Grading Page: Parsed answers, score/feedback form, adaptive trigger.Grading
Submissions Table: Filtered for real work only.Submissions

🛠️ Quick Setup

Clone & Install:Bashgit clone https://github.com/yourusername/edu-platform.git
cd edu-platform
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
Database & Migrations:Bashpython manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
Load Sample Data:
Add questions.csv to core/management/commands/ (format: topic,difficulty,question_text,hint).
Run: python manage.py load_questions questions.csv.

Run Server:Bashpython manage.py runserver
Visit http://127.0.0.1:8000/ → Welcome page.
Create users: Teachers via admin; students via register.

Debug Toolbar (Optional):
Install: pip install django-debug-toolbar.
Add to INSTALLED_APPS/MIDDLEWARE as per docs.
<img width="757" height="390" alt="image" src="https://github.com/user-attachments/assets/dd07c6f5-b0fa-43f5-ba91-7ed98d8ef1b0" />
🔧 Customization

Add ML Grading: In grade_submission, use scikit-learn to compare student code vs. samples (e.g., cosine similarity on tokenized code).
Auth: Uses Django's built-in; extend with groups for roles.
Deployment: Heroku/Render—set DEBUG=False, add gunicorn.

🤝 Contributing

Fork & clone.
Create branch: git checkout -b feature/adaptive-ui.
Commit: git commit -m "Add: High-level question filter".
Push & PR!
