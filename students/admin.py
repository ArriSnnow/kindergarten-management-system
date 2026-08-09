from django.contrib import admin

from students.models import FileNumberSequence, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'last_name', 'first_name', 'file_number', 'registration_grade', 'date_of_birth',
        'status', 'enrollment_date',
    )
    list_filter = ('status', 'gender', 'registration_grade')
    search_fields = ('last_name', 'first_name', 'file_number')
    readonly_fields = ('file_number',)


@admin.register(FileNumberSequence)
class FileNumberSequenceAdmin(admin.ModelAdmin):
    list_display = ('year', 'grade', 'last_number')
    list_filter = ('year', 'grade')
    readonly_fields = ('year', 'grade', 'last_number')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
