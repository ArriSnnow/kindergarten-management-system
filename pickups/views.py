from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import ListView

from accounts.mixins import AdminRequiredMixin
from academics.models import Class, Enrollment
from audit.models import AuditLog
from pickups.forms import PickupDateForm
from pickups.models import PickupRecord
from students.models import Student


def _picker_options(student):
    guardians = [
        (f'guardian:{link.guardian_id}', str(link.guardian))
        for link in student.guardian_links.filter(guardian__is_active=True).select_related('guardian')
    ]
    persons = [
        (f'person:{person.pk}', str(person))
        for person in student.authorized_pickups.filter(is_active=True)
    ]
    return guardians, persons


def _selected_value(pickup):
    if not pickup:
        return ''
    if pickup.guardian_id:
        return f'guardian:{pickup.guardian_id}'
    return f'person:{pickup.authorized_person_id}'


class PickupTakeView(AdminRequiredMixin, View):
    def get(self, request, class_pk):
        classe = get_object_or_404(Class, pk=class_pk)
        date = self._resolve_date(request)
        roster = classe.enrollments.filter(
            status=Enrollment.Status.ACTIVE,
        ).select_related('student').order_by('student__last_name', 'student__first_name')
        existing = {
            pickup.enrollment_id: pickup
            for pickup in PickupRecord.objects.filter(enrollment__classe=classe, date=date)
        }
        rows = []
        for enrollment in roster:
            pickup = existing.get(enrollment.pk)
            guardians, persons = _picker_options(enrollment.student)
            rows.append({
                'enrollment': enrollment,
                'pickup': pickup,
                'guardians': guardians,
                'persons': persons,
                'selected': _selected_value(pickup),
            })

        return render(request, 'pickups/take.html', {
            'classe': classe,
            'date': date,
            'rows': rows,
            'date_form': PickupDateForm(initial={'date': date}),
        })

    def post(self, request, class_pk):
        classe = get_object_or_404(Class, pk=class_pk)
        date = self._resolve_date(request)
        roster = classe.enrollments.filter(status=Enrollment.Status.ACTIVE).select_related('student')

        count = 0
        for enrollment in roster:
            value = request.POST.get(f'picker_{enrollment.pk}', '').strip()
            if not value:
                continue
            kind, _, raw_id = value.partition(':')
            if kind not in ('guardian', 'person') or not raw_id.isdigit():
                continue
            picker_id = int(raw_id)
            student = enrollment.student

            if kind == 'guardian':
                if not student.guardian_links.filter(guardian_id=picker_id, guardian__is_active=True).exists():
                    continue
                defaults_extra = {'guardian_id': picker_id, 'authorized_person_id': None}
            else:
                if not student.authorized_pickups.filter(pk=picker_id, is_active=True).exists():
                    continue
                defaults_extra = {'guardian_id': None, 'authorized_person_id': picker_id}

            note = request.POST.get(f'note_{enrollment.pk}', '').strip()
            PickupRecord.objects.update_or_create(
                enrollment=enrollment, date=date,
                defaults={'note': note, 'recorded_by': request.user, **defaults_extra},
            )
            count += 1

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            model_name='pickuprecord',
            object_id=f'classe-{classe.pk}',
            object_repr=f'{classe} — {date}',
            details=f'{count} départ(s) enregistré(s)' if count else 'Aucun départ enregistré',
        )
        messages.success(request, 'Départs enregistrés.')
        return redirect(f"{reverse('pickups:take', args=[classe.pk])}?date={date.isoformat()}")

    def _resolve_date(self, request):
        raw = request.GET.get('date') or request.POST.get('date')
        parsed = parse_date(raw) if raw else None
        today = timezone.localdate()
        if not parsed or parsed > today:
            return today
        return parsed


class StudentPickupHistoryView(AdminRequiredMixin, ListView):
    template_name = 'pickups/student_history.html'
    context_object_name = 'pickups'
    paginate_by = 30

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=kwargs['student_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return PickupRecord.objects.filter(
            enrollment__student=self.student,
        ).select_related('enrollment', 'enrollment__classe', 'enrollment__school_year', 'guardian', 'authorized_person')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.student
        return context
