from django.contrib import admin

from assessments.models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'domain', 'period', 'scale', 'score')
    list_filter = ('domain', 'period', 'scale')
    search_fields = ('enrollment__student__last_name', 'enrollment__student__first_name')
