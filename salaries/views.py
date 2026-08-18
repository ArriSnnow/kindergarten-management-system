from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView

from accounts.mixins import AdminRequiredMixin
from audit.models import AuditLog
from audit.utils import log_action
from salaries.forms import SalaryPaymentForm
from salaries.models import SalaryPayment
from staff.models import Staff


class StaffSalaryHistoryView(AdminRequiredMixin, DetailView):
    model = Staff
    pk_url_kwarg = 'staff_pk'
    template_name = 'salaries/staff_history.html'
    context_object_name = 'staff_member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.salary_payments.select_related('recorded_by', 'voided_by')
        return context


class SalaryPaymentCreateView(AdminRequiredMixin, CreateView):
    model = SalaryPayment
    form_class = SalaryPaymentForm
    template_name = 'salaries/payment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.staff_member = get_object_or_404(Staff, pk=kwargs['staff_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['staff_member'] = self.staff_member
        return context

    def get_initial(self):
        return {'date': timezone.localdate()}

    def form_valid(self, form):
        form.instance.staff = self.staff_member
        form.instance.recorded_by = self.request.user
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Paiement de salaire enregistré.')
        return response

    def get_success_url(self):
        return reverse('salaries:staff-history', args=[self.staff_member.pk])


class SalaryPaymentVoidView(AdminRequiredMixin, View):
    def post(self, request, staff_pk, pk):
        payment = get_object_or_404(SalaryPayment, pk=pk, staff_id=staff_pk)
        reason = request.POST.get('void_reason', '').strip()
        if payment.is_voided:
            messages.info(request, 'Ce paiement est déjà annulé.')
        elif not reason:
            messages.error(request, "Un motif d'annulation est requis.")
        else:
            payment.is_voided = True
            payment.void_reason = reason
            payment.voided_at = timezone.now()
            payment.voided_by = request.user
            payment.save()
            log_action(request.user, AuditLog.Action.VOID, payment, details=reason)
            messages.success(request, 'Paiement annulé.')
        return redirect('salaries:staff-history', staff_pk=staff_pk)
