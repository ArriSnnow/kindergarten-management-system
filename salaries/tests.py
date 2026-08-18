from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from salaries.models import SalaryPayment
from staff.models import Staff

User = get_user_model()


def make_staff(**kwargs):
    defaults = {
        'last_name': 'Girard',
        'first_name': 'Nadia',
        'phone': '0600000000',
    }
    defaults.update(kwargs)
    return Staff.objects.create(**defaults)


def make_salary_payment(staff=None, **kwargs):
    if staff is None:
        staff = make_staff()
    defaults = {
        'amount': Decimal('50000'), 'date': '2026-01-31', 'period': 'Janvier 2026',
        'method': SalaryPayment.Method.CASH,
    }
    defaults.update(kwargs)
    return SalaryPayment.objects.create(staff=staff, **defaults)


class SalaryPaymentModelTests(TestCase):
    def test_zero_amount_rejected_by_db(self):
        staff = make_staff()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SalaryPayment.objects.create(
                    staff=staff, amount=Decimal('0'), date='2026-01-31', period='Janvier 2026',
                    method=SalaryPayment.Method.CASH,
                )

    def test_clean_rejects_non_positive_amount(self):
        payment = SalaryPayment(
            staff=make_staff(), amount=Decimal('0'), date='2026-01-31', period='Janvier 2026',
            method=SalaryPayment.Method.CASH,
        )
        with self.assertRaises(ValidationError):
            payment.clean()

    def test_default_not_voided(self):
        payment = make_salary_payment()
        self.assertFalse(payment.is_voided)

    def test_multiple_payments_allowed_per_staff(self):
        staff = make_staff()
        make_salary_payment(staff=staff, period='Janvier 2026')
        make_salary_payment(staff=staff, period='Février 2026')
        self.assertEqual(SalaryPayment.objects.filter(staff=staff).count(), 2)


class SalariesAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.staff = make_staff()

    def test_anonymous_redirected_from_history(self):
        response = self.client.get(reverse('salaries:staff-history', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 302)

    def test_parent_forbidden_from_history(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('salaries:staff-history', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed_history(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('salaries:staff-history', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)


class SalaryPaymentCreateViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.staff = make_staff()

    def test_creates_payment(self):
        response = self.client.post(
            reverse('salaries:payment-add', args=[self.staff.pk]),
            {
                'amount': '50000', 'date': '2026-01-31', 'period': 'Janvier 2026',
                'method': SalaryPayment.Method.BANK_TRANSFER, 'note': '',
            },
        )
        self.assertRedirects(response, reverse('salaries:staff-history', args=[self.staff.pk]))
        payment = SalaryPayment.objects.get(staff=self.staff)
        self.assertEqual(payment.amount, Decimal('50000'))
        self.assertEqual(payment.recorded_by, self.admin)

    def test_logs_audit_entry(self):
        self.client.post(
            reverse('salaries:payment-add', args=[self.staff.pk]),
            {
                'amount': '50000', 'date': '2026-01-31', 'period': 'Janvier 2026',
                'method': SalaryPayment.Method.CASH, 'note': '',
            },
        )
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.CREATE, model_name='salarypayment').exists())


class SalaryPaymentVoidViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.staff = make_staff()
        self.payment = make_salary_payment(staff=self.staff)

    def _url(self):
        return reverse('salaries:payment-void', args=[self.staff.pk, self.payment.pk])

    def test_voids_payment_with_reason(self):
        response = self.client.post(self._url(), {'void_reason': 'Erreur de saisie'})
        self.assertRedirects(response, reverse('salaries:staff-history', args=[self.staff.pk]))
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.is_voided)
        self.assertEqual(self.payment.void_reason, 'Erreur de saisie')
        self.assertEqual(self.payment.voided_by, self.admin)

    def test_requires_non_empty_reason(self):
        self.client.post(self._url(), {'void_reason': '  '})
        self.payment.refresh_from_db()
        self.assertFalse(self.payment.is_voided)

    def test_cannot_double_void(self):
        self.client.post(self._url(), {'void_reason': 'Premier motif'})
        self.client.post(self._url(), {'void_reason': 'Deuxième motif'})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.void_reason, 'Premier motif')

    def test_logs_void_audit_entry(self):
        self.client.post(self._url(), {'void_reason': 'Erreur de saisie'})
        logs = AuditLog.objects.filter(action=AuditLog.Action.VOID, model_name='salarypayment')
        self.assertEqual(logs.count(), 1)

    def test_payment_row_never_deleted(self):
        self.client.post(self._url(), {'void_reason': 'Erreur de saisie'})
        self.assertEqual(SalaryPayment.objects.count(), 1)
