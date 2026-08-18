from django.contrib import admin

from salaries.models import SalaryPayment


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('staff', 'amount', 'date', 'period', 'method', 'is_voided')
    list_filter = ('method', 'is_voided', 'date')
    search_fields = ('staff__last_name', 'staff__first_name')
