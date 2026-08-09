from django.contrib import admin

from academics.models import Class, Enrollment, SchoolYear


@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ('label', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'school_year', 'grade', 'name', 'teacher')
    list_filter = ('school_year', 'grade')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'school_year', 'grade', 'classe', 'status')
    list_filter = ('school_year', 'grade', 'status')
    search_fields = ('student__last_name', 'student__first_name')
