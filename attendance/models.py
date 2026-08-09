from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from academics.models import Enrollment


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Présent'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Retard'
        EXCUSED = 'EXCUSED', 'Absence justifiée'

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField('date')
    status = models.CharField('statut', max_length=10, choices=Status.choices, default=Status.PRESENT)
    note = models.CharField('remarque', max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='attendances_recorded', verbose_name='enregistré par',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'présence'
        verbose_name_plural = 'présences'
        constraints = [
            models.UniqueConstraint(fields=['enrollment', 'date'], name='unique_attendance_per_enrollment_date'),
        ]

    def __str__(self):
        return f'{self.enrollment.student} — {self.date} ({self.get_status_display()})'

    def clean(self):
        if self.date and self.date > timezone.localdate():
            raise ValidationError({'date': "La date de présence ne peut pas être dans le futur."})
