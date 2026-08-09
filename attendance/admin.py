from django.contrib import admin

from attendance.models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'date', 'status', 'recorded_by')
    list_filter = ('status', 'date')
    search_fields = ('enrollment__student__last_name', 'enrollment__student__first_name')
