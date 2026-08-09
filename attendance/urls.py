from django.urls import path

from attendance.views import AttendanceTakeView, StudentAttendanceHistoryView

app_name = 'attendance'

urlpatterns = [
    path('classes/<int:class_pk>/', AttendanceTakeView.as_view(), name='take'),
    path('eleves/<int:student_pk>/', StudentAttendanceHistoryView.as_view(), name='student-history'),
]
