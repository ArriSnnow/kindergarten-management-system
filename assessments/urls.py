from django.urls import path

from assessments.views import AssessmentTakeView, StudentAssessmentHistoryView

app_name = 'assessments'

urlpatterns = [
    path('classes/<int:class_pk>/', AssessmentTakeView.as_view(), name='take'),
    path('eleves/<int:student_pk>/', StudentAssessmentHistoryView.as_view(), name='student-history'),
]
