from django.contrib import admin
from .models import User, Subject, Enrollment, Question, Assignment, Submission

admin.site.register(User)
admin.site.register(Subject)
admin.site.register(Enrollment)
admin.site.register(Question)
admin.site.register(Assignment)
admin.site.register(Submission)