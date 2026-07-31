from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin
from audit.models import AuditLog
from audit.utils import log_action
from guardians.forms import AuthorizedPickupPersonForm, GuardianForm, StudentGuardianForm
from guardians.models import AuthorizedPickupPerson, Guardian, StudentGuardian
from students.models import Student


class GuardianListView(AdminRequiredMixin, ListView):
    model = Guardian
    template_name = 'guardians/guardian_list.html'
    context_object_name = 'guardians'
    paginate_by = 25

    def get_queryset(self):
        queryset = Guardian.objects.all()
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(last_name__icontains=query) | Q(first_name__icontains=query))
        return queryset.order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class GuardianDetailView(AdminRequiredMixin, DetailView):
    model = Guardian
    template_name = 'guardians/guardian_detail.html'
    context_object_name = 'guardian'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_links'] = self.object.student_links.select_related('student')
        return context


class GuardianCreateView(AdminRequiredMixin, CreateView):
    model = Guardian
    form_class = GuardianForm
    template_name = 'guardians/guardian_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Tuteur ajouté avec succès.')
        return response

    def get_success_url(self):
        return reverse('guardians:detail', args=[self.object.pk])


class GuardianUpdateView(AdminRequiredMixin, UpdateView):
    model = Guardian
    form_class = GuardianForm
    template_name = 'guardians/guardian_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.UPDATE, self.object)
        messages.success(self.request, 'Fiche tuteur mise à jour.')
        return response

    def get_success_url(self):
        return reverse('guardians:detail', args=[self.object.pk])


class GuardianDeactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        guardian = get_object_or_404(Guardian, pk=pk)
        guardian.is_active = False
        guardian.save()
        log_action(request.user, AuditLog.Action.DEACTIVATE, guardian)
        messages.success(request, 'Tuteur désactivé.')
        return redirect('guardians:detail', pk=guardian.pk)


class GuardianReactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        guardian = get_object_or_404(Guardian, pk=pk)
        guardian.is_active = True
        guardian.save()
        log_action(request.user, AuditLog.Action.REACTIVATE, guardian)
        messages.success(request, 'Tuteur réactivé.')
        return redirect('guardians:detail', pk=guardian.pk)


class StudentGuardianCreateView(AdminRequiredMixin, CreateView):
    model = StudentGuardian
    form_class = StudentGuardianForm
    template_name = 'guardians/student_guardian_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=kwargs['student_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.student
        return context

    def form_valid(self, form):
        form.instance.student = self.student
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Tuteur lié à l\'élève.')
        return response

    def get_success_url(self):
        return reverse('students:detail', args=[self.student.pk])


class StudentGuardianDeleteView(AdminRequiredMixin, View):
    def post(self, request, student_pk, link_pk):
        link = get_object_or_404(StudentGuardian, pk=link_pk, student_id=student_pk)
        log_action(request.user, AuditLog.Action.DELETE, link)
        link.delete()
        messages.success(request, 'Lien tuteur-élève retiré.')
        return redirect('students:detail', pk=student_pk)


class AuthorizedPickupPersonCreateView(AdminRequiredMixin, CreateView):
    model = AuthorizedPickupPerson
    form_class = AuthorizedPickupPersonForm
    template_name = 'guardians/pickup_person_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=kwargs['student_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.student
        return context

    def form_valid(self, form):
        form.instance.student = self.student
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Personne autorisée ajoutée.')
        return response

    def get_success_url(self):
        return reverse('students:detail', args=[self.student.pk])


class AuthorizedPickupPersonUpdateView(AdminRequiredMixin, UpdateView):
    model = AuthorizedPickupPerson
    form_class = AuthorizedPickupPersonForm
    template_name = 'guardians/pickup_person_form.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return AuthorizedPickupPerson.objects.filter(student_id=self.kwargs['student_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.object.student
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.UPDATE, self.object)
        messages.success(self.request, 'Personne autorisée mise à jour.')
        return response

    def get_success_url(self):
        return reverse('students:detail', args=[self.object.student.pk])


class AuthorizedPickupPersonDeactivateView(AdminRequiredMixin, View):
    def post(self, request, student_pk, pk):
        person = get_object_or_404(AuthorizedPickupPerson, pk=pk, student_id=student_pk)
        person.is_active = False
        person.save()
        log_action(request.user, AuditLog.Action.DEACTIVATE, person)
        messages.success(request, 'Personne autorisée désactivée.')
        return redirect('students:detail', pk=student_pk)


class AuthorizedPickupPersonReactivateView(AdminRequiredMixin, View):
    def post(self, request, student_pk, pk):
        person = get_object_or_404(AuthorizedPickupPerson, pk=pk, student_id=student_pk)
        person.is_active = True
        person.save()
        log_action(request.user, AuditLog.Action.REACTIVATE, person)
        messages.success(request, 'Personne autorisée réactivée.')
        return redirect('students:detail', pk=student_pk)
