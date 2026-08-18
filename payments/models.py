from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from academics.models import Enrollment


class Fee(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.PROTECT, related_name='fee')
    amount_due = models.DecimalField('montant dû', max_digits=10, decimal_places=2)
    note = models.CharField('remarque', max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'frais de scolarité'
        verbose_name_plural = 'frais de scolarité'
        constraints = [
            models.CheckConstraint(check=models.Q(amount_due__gte=0), name='fee_amount_due_non_negative'),
        ]

    def __str__(self):
        return f'{self.enrollment} — {self.amount_due}'

    def clean(self):
        if self.amount_due is not None and self.amount_due < 0:
            raise ValidationError({'amount_due': 'Le montant dû ne peut pas être négatif.'})

    @property
    def total_paid(self):
        return self.payments.filter(is_voided=False).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    @property
    def balance(self):
        return self.amount_due - self.total_paid


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'ESPECES', 'Espèces'
        BANK_TRANSFER = 'VIREMENT', 'Virement bancaire'
        CHEQUE = 'CHEQUE', 'Chèque'
        MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile money'

    fee = models.ForeignKey(Fee, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField('montant', max_digits=10, decimal_places=2)
    date = models.DateField('date')
    method = models.CharField('moyen de paiement', max_length=20, choices=Method.choices)
    note = models.CharField('remarque', max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payments_recorded', verbose_name='enregistré par',
    )

    is_voided = models.BooleanField('annulé', default=False)
    void_reason = models.CharField('motif d\'annulation', max_length=255, blank=True)
    voided_at = models.DateTimeField('annulé le', null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payments_voided', verbose_name='annulé par',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'paiement'
        verbose_name_plural = 'paiements'
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name='payment_amount_positive'),
        ]

    def __str__(self):
        return f'{self.fee.enrollment.student} — {self.amount} ({self.date})'

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Le montant doit être positif.'})
