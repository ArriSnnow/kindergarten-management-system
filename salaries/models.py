from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from staff.models import Staff


class SalaryPayment(models.Model):
    class Method(models.TextChoices):
        CASH = 'ESPECES', 'Espèces'
        BANK_TRANSFER = 'VIREMENT', 'Virement bancaire'
        CHEQUE = 'CHEQUE', 'Chèque'
        MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile money'

    staff = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name='salary_payments')
    amount = models.DecimalField('montant', max_digits=10, decimal_places=2)
    date = models.DateField('date')
    period = models.CharField('période', max_length=20, help_text='ex. Janvier 2026')
    method = models.CharField('moyen de paiement', max_length=20, choices=Method.choices)
    note = models.CharField('remarque', max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='salary_payments_recorded', verbose_name='enregistré par',
    )

    is_voided = models.BooleanField('annulé', default=False)
    void_reason = models.CharField('motif d\'annulation', max_length=255, blank=True)
    voided_at = models.DateTimeField('annulé le', null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='salary_payments_voided', verbose_name='annulé par',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'paiement de salaire'
        verbose_name_plural = 'paiements de salaire'
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name='salary_payment_amount_positive'),
        ]

    def __str__(self):
        return f'{self.staff} — {self.amount} ({self.period})'

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Le montant doit être positif.'})
