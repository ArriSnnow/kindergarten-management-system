from django.contrib import admin

from students.models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'date_of_birth', 'status', 'enrollment_date')
    list_filter = ('status', 'gender')
    search_fields = ('last_name', 'first_name')
