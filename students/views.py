from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin
from audit.models import AuditLog
from audit.utils import log_action
from students.forms import StudentArchiveForm, StudentForm
from students.models import Student


class StudentListView(AdminRequiredMixin, ListView):
    model = Student
    template_name = 'students/student_list.html'
    context_object_name = 'students'
    paginate_by = 25

    def get_queryset(self):
        queryset = Student.objects.all()
        query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '')
        if query:
            queryset = queryset.filter(Q(last_name__icontains=query) | Q(first_name__icontains=query))
        if status in Student.Status.values:
            queryset = queryset.filter(status=status)
        return queryset.order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')
        context['status_choices'] = Student.Status.choices
        return context


class StudentDetailView(AdminRequiredMixin, DetailView):
    model = Student
    template_name = 'students/student_detail.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['guardian_links'] = self.object.guardian_links.select_related('guardian')
        context['authorized_pickups'] = self.object.authorized_pickups.all()
        context['enrollments'] = self.object.enrollments.select_related('school_year', 'classe')
        return context


class StudentCreateView(AdminRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, 'Élève ajouté avec succès.')
        return response

    def get_success_url(self):
        return reverse('students:detail', args=[self.object.pk])


class StudentUpdateView(AdminRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.UPDATE, self.object)
        messages.success(self.request, 'Fiche élève mise à jour.')
        return response

    def get_success_url(self):
        return reverse('students:detail', args=[self.object.pk])


class StudentArchiveView(AdminRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        form = StudentArchiveForm()
        return self._render(request, student, form)

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        form = StudentArchiveForm(request.POST)
        if not form.is_valid():
            return self._render(request, student, form)

        student.status = Student.Status.ARCHIVED
        student.archived_at = timezone.now()
        student.archive_reason = form.cleaned_data['archive_reason']
        student.save()
        log_action(request.user, AuditLog.Action.ARCHIVE, student, details=student.archive_reason)
        messages.success(request, 'Élève archivé.')
        return redirect('students:detail', pk=student.pk)

    def _render(self, request, student, form):
        return render(request, 'students/student_archive.html', {'student': student, 'form': form})


class StudentReactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        student.status = Student.Status.ACTIVE
        student.archived_at = None
        student.archive_reason = ''
        student.save()
        log_action(request.user, AuditLog.Action.REACTIVATE, student)
        messages.success(request, 'Élève réactivé.')
        return redirect('students:detail', pk=student.pk)
