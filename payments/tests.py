import itertools
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from academics.models import Class, Enrollment, SchoolYear
from audit.models import AuditLog
from payments.models import Fee, Payment
from students.models import Student

User = get_user_model()


_school_year_counter = itertools.count(2020)


def make_school_year(**kwargs):
    year = next(_school_year_counter)
    defaults = {
        'label': f'{year}-{year + 1}',
        'start_date': f'{year}-09-01',
        'end_date': f'{year + 1}-07-01',
    }
    defaults.update(kwargs)
    return SchoolYear.objects.create(**defaults)


def make_student(**kwargs):
    defaults = {
        'last_name': 'Dupont',
        'first_name': 'Léa',
        'date_of_birth': '2021-03-10',
        'gender': Student.Gender.GIRL,
        'enrollment_date': '2024-09-01',
        'registration_grade': Student.RegistrationGrade.PS,
    }
    defaults.update(kwargs)
    return Student.objects.create(**defaults)


def make_class(school_year=None, **kwargs):
    if school_year is None:
        school_year = make_school_year()
    defaults = {'grade': Student.RegistrationGrade.PS}
    defaults.update(kwargs)
    return Class.objects.create(school_year=school_year, **defaults)


def make_enrollment(student=None, school_year=None, **kwargs):
    if student is None:
        student = make_student()
    if school_year is None:
        school_year = make_school_year()
    defaults = {'grade': Student.RegistrationGrade.PS}
    defaults.update(kwargs)
    return Enrollment.objects.create(student=student, school_year=school_year, **defaults)


def make_fee(enrollment=None, **kwargs):
    if enrollment is None:
        enrollment = make_enrollment()
    defaults = {'amount_due': Decimal('100000')}
    defaults.update(kwargs)
    return Fee.objects.create(enrollment=enrollment, **defaults)


def make_payment(fee=None, **kwargs):
    if fee is None:
        fee = make_fee()
    defaults = {'amount': Decimal('20000'), 'date': '2026-01-15', 'method': Payment.Method.CASH}
    defaults.update(kwargs)
    return Payment.objects.create(fee=fee, **defaults)


class FeeModelTests(TestCase):
    def test_one_fee_per_enrollment(self):
        enrollment = make_enrollment()
        make_fee(enrollment=enrollment)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Fee.objects.create(enrollment=enrollment, amount_due=Decimal('1000'))

    def test_negative_amount_due_rejected_by_db(self):
        enrollment = make_enrollment()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Fee.objects.create(enrollment=enrollment, amount_due=Decimal('-1'))

    def test_clean_rejects_negative_amount_due(self):
        fee = Fee(enrollment=make_enrollment(), amount_due=Decimal('-1'))
        with self.assertRaises(ValidationError):
            fee.clean()

    def test_total_paid_excludes_voided_payments(self):
        fee = make_fee(amount_due=Decimal('100000'))
        make_payment(fee=fee, amount=Decimal('30000'))
        voided = make_payment(fee=fee, amount=Decimal('20000'))
        voided.is_voided = True
        voided.save()
        self.assertEqual(fee.total_paid, Decimal('30000'))

    def test_total_paid_zero_when_no_payments(self):
        fee = make_fee()
        self.assertEqual(fee.total_paid, Decimal('0'))

    def test_balance_computed_from_payments(self):
        fee = make_fee(amount_due=Decimal('100000'))
        make_payment(fee=fee, amount=Decimal('40000'))
        self.assertEqual(fee.balance, Decimal('60000'))


class PaymentModelTests(TestCase):
    def test_zero_amount_rejected_by_db(self):
        fee = make_fee()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Payment.objects.create(fee=fee, amount=Decimal('0'), date='2026-01-15', method=Payment.Method.CASH)

    def test_clean_rejects_non_positive_amount(self):
        payment = Payment(fee=make_fee(), amount=Decimal('0'), date='2026-01-15', method=Payment.Method.CASH)
        with self.assertRaises(ValidationError):
            payment.clean()

    def test_default_not_voided(self):
        payment = make_payment()
        self.assertFalse(payment.is_voided)


class PaymentsAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.enrollment = make_enrollment()

    def test_anonymous_redirected_from_fee_detail(self):
        response = self.client.get(reverse('payments:fee-detail', args=[self.enrollment.pk]))
        self.assertEqual(response.status_code, 302)

    def test_parent_forbidden_from_fee_detail(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('payments:fee-detail', args=[self.enrollment.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed_fee_detail(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('payments:fee-detail', args=[self.enrollment.pk]))
        self.assertEqual(response.status_code, 200)


class FeeSetViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.enrollment = make_enrollment()

    def test_creates_fee(self):
        response = self.client.post(
            reverse('payments:fee-set', args=[self.enrollment.pk]),
            {'amount_due': '150000', 'note': 'Année complète'},
        )
        self.assertRedirects(response, reverse('payments:fee-detail', args=[self.enrollment.pk]))
        fee = Fee.objects.get(enrollment=self.enrollment)
        self.assertEqual(fee.amount_due, Decimal('150000'))

    def test_updates_existing_fee_not_duplicate(self):
        make_fee(enrollment=self.enrollment, amount_due=Decimal('100000'))
        self.client.post(
            reverse('payments:fee-set', args=[self.enrollment.pk]),
            {'amount_due': '120000', 'note': ''},
        )
        self.assertEqual(Fee.objects.filter(enrollment=self.enrollment).count(), 1)
        self.assertEqual(Fee.objects.get(enrollment=self.enrollment).amount_due, Decimal('120000'))

    def test_logs_create_audit_entry(self):
        self.client.post(reverse('payments:fee-set', args=[self.enrollment.pk]), {'amount_due': '150000', 'note': ''})
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.CREATE, model_name='fee').exists())

    def test_logs_update_audit_entry(self):
        make_fee(enrollment=self.enrollment)
        self.client.post(reverse('payments:fee-set', args=[self.enrollment.pk]), {'amount_due': '999', 'note': ''})
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.UPDATE, model_name='fee').exists())


class PaymentCreateViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.enrollment = make_enrollment()

    def test_redirects_to_fee_set_when_no_fee_exists(self):
        response = self.client.get(reverse('payments:payment-add', args=[self.enrollment.pk]))
        self.assertRedirects(response, reverse('payments:fee-set', args=[self.enrollment.pk]))

    def test_creates_payment_when_fee_exists(self):
        make_fee(enrollment=self.enrollment)
        response = self.client.post(
            reverse('payments:payment-add', args=[self.enrollment.pk]),
            {'amount': '25000', 'date': '2026-01-15', 'method': Payment.Method.MOBILE_MONEY, 'note': 'Acompte'},
        )
        self.assertRedirects(response, reverse('payments:fee-detail', args=[self.enrollment.pk]))
        payment = Payment.objects.get(fee__enrollment=self.enrollment)
        self.assertEqual(payment.amount, Decimal('25000'))
        self.assertEqual(payment.recorded_by, self.admin)

    def test_logs_audit_entry(self):
        make_fee(enrollment=self.enrollment)
        self.client.post(
            reverse('payments:payment-add', args=[self.enrollment.pk]),
            {'amount': '25000', 'date': '2026-01-15', 'method': Payment.Method.CASH, 'note': ''},
        )
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.CREATE, model_name='payment').exists())


class PaymentVoidViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.fee = make_fee()
        self.payment = make_payment(fee=self.fee)

    def _url(self):
        return reverse('payments:payment-void', args=[self.fee.enrollment.pk, self.payment.pk])

    def test_voids_payment_with_reason(self):
        response = self.client.post(self._url(), {'void_reason': 'Erreur de saisie'})
        self.assertRedirects(response, reverse('payments:fee-detail', args=[self.fee.enrollment.pk]))
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.is_voided)
        self.assertEqual(self.payment.void_reason, 'Erreur de saisie')
        self.assertEqual(self.payment.voided_by, self.admin)
        self.assertIsNotNone(self.payment.voided_at)

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
        logs = AuditLog.objects.filter(action=AuditLog.Action.VOID, model_name='payment')
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().details, 'Erreur de saisie')

    def test_payment_row_never_deleted(self):
        self.client.post(self._url(), {'void_reason': 'Erreur de saisie'})
        self.assertEqual(Payment.objects.count(), 1)
