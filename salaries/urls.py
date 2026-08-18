from django.urls import path

from salaries.views import SalaryPaymentCreateView, SalaryPaymentVoidView, StaffSalaryHistoryView

app_name = 'salaries'

urlpatterns = [
    path('personnel/<int:staff_pk>/', StaffSalaryHistoryView.as_view(), name='staff-history'),
    path('personnel/<int:staff_pk>/ajouter/', SalaryPaymentCreateView.as_view(), name='payment-add'),
    path('personnel/<int:staff_pk>/<int:pk>/annuler/', SalaryPaymentVoidView.as_view(), name='payment-void'),
]
