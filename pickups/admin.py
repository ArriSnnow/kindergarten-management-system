from django.contrib import admin

from pickups.models import PickupRecord


@admin.register(PickupRecord)
class PickupRecordAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'date', 'picked_up_by', 'recorded_by')
    list_filter = ('date',)
    search_fields = ('enrollment__student__last_name', 'enrollment__student__first_name')
