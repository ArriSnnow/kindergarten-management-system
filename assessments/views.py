from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from accounts.mixins import AdminRequiredMixin
from academics.models import Class, Enrollment
from assessments.forms import AssessmentFilterForm
from assessments.models import Assessment
from audit.models import AuditLog
from students.models import Student


class AssessmentTakeView(AdminRequiredMixin, View):
    def get(self, request, class_pk):
        classe = get_object_or_404(Class, pk=class_pk)
        domain = request.GET.get('domain', '').strip()
        period = request.GET.get('period', '').strip()
        rows = []
        if domain and period:
            roster = classe.enrollments.filter(
                status=Enrollment.Status.ACTIVE,
            ).select_related('student').order_by('student__last_name', 'student__first_name')
            existing = {
                assessment.enrollment_id: assessment
                for assessment in Assessment.objects.filter(enrollment__classe=classe, domain=domain, period=period)
            }
            rows = [(enrollment, existing.get(enrollment.pk)) for enrollment in roster]

        return render(request, 'assessments/take.html', {
            'classe': classe,
            'domain': domain,
            'period': period,
            'rows': rows,
            'scales': Assessment.Scale.choices,
            'filter_form': AssessmentFilterForm(initial={'domain': domain, 'period': period}),
        })

    def post(self, request, class_pk):
        classe = get_object_or_404(Class, pk=class_pk)
        domain = request.POST.get('domain', '').strip()
        period = request.POST.get('period', '').strip()
        if not domain or not period:
            messages.error(request, 'Le domaine et la période sont requis.')
            return redirect(reverse('assessments:take', args=[classe.pk]))

        roster = classe.enrollments.filter(status=Enrollment.Status.ACTIVE)
        count = 0
        for enrollment in roster:
            scale = request.POST.get(f'scale_{enrollment.pk}', '').strip()
            if scale not in Assessment.Scale.values:
                scale = ''
            score_raw = request.POST.get(f'score_{enrollment.pk}', '').strip()
            score = None
            if score_raw:
                try:
                    score = Decimal(score_raw)
                except InvalidOperation:
                    score = None
            note = request.POST.get(f'note_{enrollment.pk}', '').strip()

            if not scale and score is None and not note:
                continue

            Assessment.objects.update_or_create(
                enrollment=enrollment, domain=domain, period=period,
                defaults={'scale': scale, 'score': score, 'note': note, 'recorded_by': request.user},
            )
            count += 1

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            model_name='assessment',
            object_id=f'classe-{classe.pk}',
            object_repr=f'{classe} — {domain} — {period}',
            details=f'{count} évaluation(s) enregistrée(s)' if count else 'Aucune évaluation enregistrée',
        )
        messages.success(request, 'Évaluations enregistrées.')
        return redirect(f"{reverse('assessments:take', args=[classe.pk])}?domain={domain}&period={period}")


class StudentAssessmentHistoryView(AdminRequiredMixin, ListView):
    template_name = 'assessments/student_history.html'
    context_object_name = 'assessments'
    paginate_by = 30

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=kwargs['student_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Assessment.objects.filter(
            enrollment__student=self.student,
        ).select_related('enrollment', 'enrollment__classe', 'enrollment__school_year')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.student
        return context
