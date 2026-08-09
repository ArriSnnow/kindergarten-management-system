from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.views.generic import CreateView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin
from audit.models import AuditLog
from audit.utils import log_action
from staff.forms import StaffForm
from staff.models import Staff


class StaffListView(AdminRequiredMixin, ListView):
    model = Staff
    template_name = 'staff/staff_list.html'
    context_object_name = 'staff_members'
    paginate_by = 25

    def get_queryset(self):
        queryset = Staff.objects.all()
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(last_name__icontains=query) | Q(first_name__icontains=query))
        return queryset.order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class StaffCreateView(AdminRequiredMixin, CreateView):
    model = Staff
    form_class = StaffForm
    template_name = 'staff/staff_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Membre du personnel ajouté.')
        return response

    def get_success_url(self):
        return reverse('staff:list')


class StaffUpdateView(AdminRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffForm
    template_name = 'staff/staff_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.UPDATE, self.object)
        messages.success(self.request, 'Fiche personnel mise à jour.')
        return response

    def get_success_url(self):
        return reverse('staff:list')
