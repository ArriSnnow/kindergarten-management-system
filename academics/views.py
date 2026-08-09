from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin
from audit.models import AuditLog
from audit.utils import log_action
from academics.forms import ClassForm, EnrollmentForm, EnrollmentWithdrawForm, SchoolYearForm
from academics.models import Class, Enrollment, SchoolYear
from students.models import Student


class SchoolYearListView(AdminRequiredMixin, ListView):
    model = SchoolYear
    template_name = 'academics/schoolyear_list.html'
    context_object_name = 'school_years'


class SchoolYearCreateView(AdminRequiredMixin, CreateView):
    model = SchoolYear
    form_class = SchoolYearForm
    template_name = 'academics/schoolyear_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Année scolaire ajoutée.')
        return response

    def get_success_url(self):
        return reverse('academics:schoolyear-list')


class SchoolYearUpdateView(AdminRequiredMixin, UpdateView):
    model = SchoolYear
    form_class = SchoolYearForm
    template_name = 'academics/schoolyear_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.UPDATE, self.object)
        messages.success(self.request, 'Année scolaire mise à jour.')
        return response

    def get_success_url(self):
        return reverse('academics:schoolyear-list')


class SchoolYearSetCurrentView(AdminRequiredMixin, View):
    def post(self, request, pk):
        school_year = get_object_or_404(SchoolYear, pk=pk)
        school_year.is_current = True
        school_year.save()
        log_action(request.user, AuditLog.Action.UPDATE, school_year, details='Définie comme année courante')
        messages.success(request, f'{school_year} définie comme année courante.')
        return redirect('academics:schoolyear-list')


class ClassListView(AdminRequiredMixin, ListView):
    model = Class
    template_name = 'academics/class_list.html'
    context_object_name = 'classes'

    def get_queryset(self):
        queryset = Class.objects.select_related('school_year', 'teacher')
        year_id = self.request.GET.get('annee')
        if year_id:
            queryset = queryset.filter(school_year_id=year_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_years'] = SchoolYear.objects.all()
        context['selected_year'] = self.request.GET.get('annee', '')
        return context


class ClassDetailView(AdminRequiredMixin, DetailView):
    model = Class
    template_name = 'academics/class_detail.html'
    context_object_name = 'classe'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roster'] = self.object.enrollments.filter(
            status=Enrollment.Status.ACTIVE,
        ).select_related('student')
        return context


class ClassCreateView(AdminRequiredMixin, CreateView):
    model = Class
    form_class = ClassForm
    template_name = 'academics/class_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Classe ajoutée.')
        return response

    def get_success_url(self):
        return reverse('academics:class-detail', args=[self.object.pk])


class ClassUpdateView(AdminRequiredMixin, UpdateView):
    model = Class
    form_class = ClassForm
    template_name = 'academics/class_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.UPDATE, self.object)
        messages.success(self.request, 'Classe mise à jour.')
        return response

    def get_success_url(self):
        return reverse('academics:class-detail', args=[self.object.pk])


class EnrollmentCreateView(AdminRequiredMixin, CreateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'academics/enrollment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=kwargs['student_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        current_year = SchoolYear.objects.filter(is_current=True).first()
        if current_year:
            initial['school_year'] = current_year
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.student
        return context

    def form_valid(self, form):
        form.instance.student = self.student
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Élève inscrit.')
        return response

    def get_success_url(self):
        return reverse('students:detail', args=[self.student.pk])


class EnrollmentUpdateView(AdminRequiredMixin, UpdateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'academics/enrollment_form.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return Enrollment.objects.filter(student_id=self.kwargs['student_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.object.student
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.UPDATE, self.object)
        messages.success(self.request, 'Inscription mise à jour.')
        return response

    def get_success_url(self):
        return reverse('students:detail', args=[self.object.student.pk])


class EnrollmentWithdrawView(AdminRequiredMixin, View):
    def get(self, request, student_pk, pk):
        enrollment = get_object_or_404(Enrollment, pk=pk, student_id=student_pk)
        form = EnrollmentWithdrawForm()
        return self._render(request, enrollment, form)

    def post(self, request, student_pk, pk):
        enrollment = get_object_or_404(Enrollment, pk=pk, student_id=student_pk)
        form = EnrollmentWithdrawForm(request.POST)
        if not form.is_valid():
            return self._render(request, enrollment, form)

        enrollment.status = Enrollment.Status.WITHDRAWN
        enrollment.withdrawn_at = timezone.now()
        enrollment.withdrawal_reason = form.cleaned_data['withdrawal_reason']
        enrollment.save()
        log_action(request.user, AuditLog.Action.ARCHIVE, enrollment, details=enrollment.withdrawal_reason)
        messages.success(request, 'Inscription retirée.')
        return redirect('students:detail', pk=student_pk)

    def _render(self, request, enrollment, form):
        return render(request, 'academics/enrollment_withdraw.html', {'enrollment': enrollment, 'form': form})
