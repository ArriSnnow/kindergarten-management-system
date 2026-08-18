from django.contrib import admin

from payments.models import Fee, Payment


@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'amount_due', 'total_paid', 'balance')
    search_fields = ('enrollment__student__last_name', 'enrollment__student__first_name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('fee', 'amount', 'date', 'method', 'is_voided', 'recorded_by')
    list_filter = ('method', 'is_voided', 'date')
    search_fields = ('fee__enrollment__student__last_name', 'fee__enrollment__student__first_name')
