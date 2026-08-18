from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from academics.models import Enrollment
from guardians.models import AuthorizedPickupPerson, Guardian


class PickupRecord(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='pickups')
    date = models.DateField('date')
    guardian = models.ForeignKey(
        Guardian, on_delete=models.PROTECT, null=True, blank=True, related_name='pickups',
        verbose_name='tuteur',
    )
    authorized_person = models.ForeignKey(
        AuthorizedPickupPerson, on_delete=models.PROTECT, null=True, blank=True, related_name='pickups',
        verbose_name='personne autorisée',
    )
    note = models.CharField('remarque', max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pickups_recorded', verbose_name='enregistré par',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'départ'
        verbose_name_plural = 'départs'
        constraints = [
            models.UniqueConstraint(fields=['enrollment', 'date'], name='unique_pickup_per_enrollment_date'),
            models.CheckConstraint(
                check=(
                    models.Q(guardian__isnull=False, authorized_person__isnull=True)
                    | models.Q(guardian__isnull=True, authorized_person__isnull=False)
                ),
                name='pickup_exactly_one_person',
            ),
        ]

    def __str__(self):
        return f'{self.enrollment.student} — {self.date} ({self.picked_up_by})'

    @property
    def picked_up_by(self):
        return self.guardian or self.authorized_person

    def clean(self):
        if self.date and self.date > timezone.localdate():
            raise ValidationError({'date': "La date de départ ne peut pas être dans le futur."})
        if bool(self.guardian_id) == bool(self.authorized_person_id):
            raise ValidationError("Sélectionnez exactement une personne (tuteur ou personne autorisée).")
        student = self.enrollment.student
        if self.guardian_id and not student.guardian_links.filter(guardian_id=self.guardian_id).exists():
            raise ValidationError({'guardian': "Ce tuteur n'est pas lié à cet élève."})
        if self.authorized_person_id and self.authorized_person.student_id != student.pk:
            raise ValidationError({'authorized_person': "Cette personne n'est pas autorisée pour cet élève."})
