from django.conf import settings
from django.db import models

from academics.models import Enrollment


class Assessment(models.Model):
    class Scale(models.TextChoices):
        EXCELLENT = 'EXCELLENT', 'Excellent'
        TRES_BIEN = 'TRES_BIEN', 'Très bien'
        BIEN = 'BIEN', 'Bien'
        EN_DEVELOPPEMENT = 'EN_DEVELOPPEMENT', 'En développement'
        BESOIN_DE_SOUTIEN = 'BESOIN_DE_SOUTIEN', 'Besoin de soutien'

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='assessments')
    domain = models.CharField('domaine', max_length=100)
    period = models.CharField('période', max_length=50)
    scale = models.CharField('appréciation', max_length=20, choices=Scale.choices, blank=True)
    score = models.DecimalField('note', max_digits=5, decimal_places=2, null=True, blank=True)
    note = models.CharField('remarque', max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assessments_recorded', verbose_name='enregistré par',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'évaluation'
        verbose_name_plural = 'évaluations'
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment', 'domain', 'period'], name='unique_assessment_per_enrollment_domain_period',
            ),
            models.CheckConstraint(check=models.Q(score__gte=0), name='assessment_score_non_negative'),
        ]

    def __str__(self):
        return f'{self.enrollment.student} — {self.domain} ({self.period})'
