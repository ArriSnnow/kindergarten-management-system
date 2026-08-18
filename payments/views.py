from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView

from accounts.mixins import AdminRequiredMixin
from academics.models import Enrollment
from audit.models import AuditLog
from audit.utils import log_action
from payments.forms import FeeForm, PaymentForm
from payments.models import Fee, Payment


class FeeDetailView(AdminRequiredMixin, DetailView):
    model = Enrollment
    pk_url_kwarg = 'enrollment_pk'
    template_name = 'payments/fee_detail.html'
    context_object_name = 'enrollment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fee = getattr(self.object, 'fee', None)
        context['fee'] = fee
        context['payments'] = fee.payments.select_related('recorded_by', 'voided_by') if fee else []
        return context


class FeeSetView(AdminRequiredMixin, View):
    def get(self, request, enrollment_pk):
        enrollment = get_object_or_404(Enrollment, pk=enrollment_pk)
        form = FeeForm(instance=getattr(enrollment, 'fee', None))
        return render(request, 'payments/fee_form.html', {'enrollment': enrollment, 'form': form})

    def post(self, request, enrollment_pk):
        enrollment = get_object_or_404(Enrollment, pk=enrollment_pk)
        fee = getattr(enrollment, 'fee', None)
        creating = fee is None
        form = FeeForm(request.POST, instance=fee)
        if form.is_valid():
            fee = form.save(commit=False)
            fee.enrollment = enrollment
            fee.save()
            log_action(request.user, AuditLog.Action.CREATE if creating else AuditLog.Action.UPDATE, fee)
            messages.success(request, 'Montant dû enregistré.')
            return redirect('payments:fee-detail', enrollment_pk=enrollment.pk)
        return render(request, 'payments/fee_form.html', {'enrollment': enrollment, 'form': form})


class PaymentCreateView(AdminRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.enrollment = get_object_or_404(Enrollment, pk=kwargs['enrollment_pk'])
        self.fee = getattr(self.enrollment, 'fee', None)
        if self.fee is None:
            messages.error(request, "Définissez d'abord le montant dû avant d'enregistrer un paiement.")
            return redirect('payments:fee-set', enrollment_pk=self.enrollment.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enrollment'] = self.enrollment
        return context

    def get_initial(self):
        return {'date': timezone.localdate()}

    def form_valid(self, form):
        form.instance.fee = self.fee
        form.instance.recorded_by = self.request.user
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Paiement enregistré.')
        return response

    def get_success_url(self):
        return reverse('payments:fee-detail', args=[self.enrollment.pk])


class PaymentVoidView(AdminRequiredMixin, View):
    def post(self, request, enrollment_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, fee__enrollment_id=enrollment_pk)
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
        return redirect('payments:fee-detail', enrollment_pk=enrollment_pk)
