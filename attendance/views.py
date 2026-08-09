from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import ListView

from accounts.mixins import AdminRequiredMixin
from academics.models import Class, Enrollment
from attendance.forms import AttendanceDateForm
from attendance.models import Attendance
from audit.models import AuditLog
from students.models import Student


class AttendanceTakeView(AdminRequiredMixin, View):
    def get(self, request, class_pk):
        classe = get_object_or_404(Class, pk=class_pk)
        date = self._resolve_date(request)
        roster = classe.enrollments.filter(
            status=Enrollment.Status.ACTIVE,
        ).select_related('student').order_by('student__last_name', 'student__first_name')
        existing = {
            attendance.enrollment_id: attendance
            for attendance in Attendance.objects.filter(enrollment__classe=classe, date=date)
        }
        rows = [(enrollment, existing.get(enrollment.pk)) for enrollment in roster]

        return render(request, 'attendance/take.html', {
            'classe': classe,
            'date': date,
            'rows': rows,
            'statuses': Attendance.Status.choices,
            'date_form': AttendanceDateForm(initial={'date': date}),
        })

    def post(self, request, class_pk):
        classe = get_object_or_404(Class, pk=class_pk)
        date = self._resolve_date(request)
        roster = classe.enrollments.filter(status=Enrollment.Status.ACTIVE)

        counts = {status: 0 for status, _ in Attendance.Status.choices}
        for enrollment in roster:
            status = request.POST.get(f'status_{enrollment.pk}', Attendance.Status.PRESENT)
            if status not in Attendance.Status.values:
                continue
            note = request.POST.get(f'note_{enrollment.pk}', '').strip()
            Attendance.objects.update_or_create(
                enrollment=enrollment, date=date,
                defaults={'status': status, 'note': note, 'recorded_by': request.user},
            )
            counts[status] += 1

        summary = ', '.join(
            f'{count} {label.lower()}' for status, label in Attendance.Status.choices if (count := counts[status])
        )
        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            model_name='attendance',
            object_id=f'classe-{classe.pk}',
            object_repr=f'{classe} — {date}',
            details=f'Présences enregistrées ({summary})' if summary else 'Présences enregistrées',
        )
        messages.success(request, 'Présences enregistrées.')
        return redirect(f"{reverse('attendance:take', args=[classe.pk])}?date={date.isoformat()}")

    def _resolve_date(self, request):
        raw = request.GET.get('date') or request.POST.get('date')
        parsed = parse_date(raw) if raw else None
        today = timezone.localdate()
        if not parsed or parsed > today:
            return today
        return parsed


class StudentAttendanceHistoryView(AdminRequiredMixin, ListView):
    template_name = 'attendance/student_history.html'
    context_object_name = 'attendances'
    paginate_by = 30

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=kwargs['student_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Attendance.objects.filter(
            enrollment__student=self.student,
        ).select_related('enrollment', 'enrollment__classe', 'enrollment__school_year')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.student
        return context
