import itertools
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from academics.models import Class, Enrollment, SchoolYear
from audit.models import AuditLog
from guardians.models import AuthorizedPickupPerson, Guardian, StudentGuardian
from pickups.models import PickupRecord
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


def make_guardian(**kwargs):
    defaults = {
        'last_name': 'Petit',
        'first_name': 'Claire',
        'phone': '0600000000',
    }
    defaults.update(kwargs)
    return Guardian.objects.create(**defaults)


def make_authorized_person(student, **kwargs):
    defaults = {
        'last_name': 'Grand',
        'first_name': 'Marc',
        'relationship': 'Voisin',
        'phone': '0611111111',
    }
    defaults.update(kwargs)
    return AuthorizedPickupPerson.objects.create(student=student, **defaults)


class PickupRecordModelTests(TestCase):
    def test_unique_per_enrollment_date(self):
        enrollment = make_enrollment()
        guardian = make_guardian()
        StudentGuardian.objects.create(
            student=enrollment.student, guardian=guardian,
            relationship_type=StudentGuardian.RelationshipType.MOTHER,
        )
        PickupRecord.objects.create(enrollment=enrollment, date='2026-01-15', guardian=guardian)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PickupRecord.objects.create(enrollment=enrollment, date='2026-01-15', guardian=guardian)

    def test_check_constraint_requires_exactly_one_person(self):
        enrollment = make_enrollment()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PickupRecord.objects.create(enrollment=enrollment, date='2026-01-15')

    def test_check_constraint_rejects_both_set(self):
        enrollment = make_enrollment()
        guardian = make_guardian()
        person = make_authorized_person(enrollment.student)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PickupRecord.objects.create(
                    enrollment=enrollment, date='2026-01-15', guardian=guardian, authorized_person=person,
                )

    def test_clean_rejects_future_date(self):
        enrollment = make_enrollment()
        guardian = make_guardian()
        pickup = PickupRecord(
            enrollment=enrollment, date=timezone.localdate() + timedelta(days=1), guardian=guardian,
        )
        with self.assertRaises(ValidationError):
            pickup.clean()

    def test_clean_rejects_guardian_not_linked_to_student(self):
        enrollment = make_enrollment()
        guardian = make_guardian()
        pickup = PickupRecord(enrollment=enrollment, date=timezone.localdate(), guardian=guardian)
        with self.assertRaises(ValidationError):
            pickup.clean()

    def test_clean_rejects_person_not_authorized_for_student(self):
        enrollment = make_enrollment()
        other_student = make_student(last_name='Autre')
        person = make_authorized_person(other_student)
        pickup = PickupRecord(enrollment=enrollment, date=timezone.localdate(), authorized_person=person)
        with self.assertRaises(ValidationError):
            pickup.clean()

    def test_clean_accepts_linked_guardian(self):
        enrollment = make_enrollment()
        guardian = make_guardian()
        StudentGuardian.objects.create(
            student=enrollment.student, guardian=guardian,
            relationship_type=StudentGuardian.RelationshipType.MOTHER,
        )
        pickup = PickupRecord(enrollment=enrollment, date=timezone.localdate(), guardian=guardian)
        pickup.clean()

    def test_picked_up_by_returns_guardian_or_person(self):
        enrollment = make_enrollment()
        guardian = make_guardian()
        pickup = PickupRecord.objects.create(enrollment=enrollment, date='2026-01-15', guardian=guardian)
        self.assertEqual(pickup.picked_up_by, guardian)


class PickupAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.classe = make_class()
        self.student = make_student()

    def test_anonymous_redirected_from_take_view(self):
        response = self.client.get(reverse('pickups:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 302)

    def test_parent_forbidden_from_take_view(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('pickups:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 403)

    def test_parent_forbidden_from_history_view(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('pickups:student-history', args=[self.student.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed_take_view(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('pickups:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 200)


class PickupTakeFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.classe = make_class()
        self.student = make_student()
        self.enrollment = make_enrollment(
            student=self.student, school_year=self.classe.school_year, classe=self.classe,
        )
        self.guardian = make_guardian()
        StudentGuardian.objects.create(
            student=self.student, guardian=self.guardian,
            relationship_type=StudentGuardian.RelationshipType.MOTHER,
        )
        self.person = make_authorized_person(self.student)
        self.date = '2026-01-15'

    def _url(self):
        return reverse('pickups:take', args=[self.classe.pk])

    def test_take_creates_record_for_guardian(self):
        response = self.client.post(self._url(), {
            'date': self.date,
            f'picker_{self.enrollment.pk}': f'guardian:{self.guardian.pk}',
        })
        self.assertRedirects(response, f'{self._url()}?date={self.date}', fetch_redirect_response=False)
        pickup = PickupRecord.objects.get(enrollment=self.enrollment, date=self.date)
        self.assertEqual(pickup.guardian, self.guardian)
        self.assertIsNone(pickup.authorized_person)

    def test_take_creates_record_for_authorized_person(self):
        self.client.post(self._url(), {
            'date': self.date,
            f'picker_{self.enrollment.pk}': f'person:{self.person.pk}',
        })
        pickup = PickupRecord.objects.get(enrollment=self.enrollment, date=self.date)
        self.assertEqual(pickup.authorized_person, self.person)
        self.assertIsNone(pickup.guardian)

    def test_empty_selection_creates_no_record(self):
        self.client.post(self._url(), {
            'date': self.date,
            f'picker_{self.enrollment.pk}': '',
        })
        self.assertEqual(PickupRecord.objects.count(), 0)

    def test_unauthorized_guardian_id_is_ignored(self):
        other_guardian = make_guardian(last_name='Etranger')
        self.client.post(self._url(), {
            'date': self.date,
            f'picker_{self.enrollment.pk}': f'guardian:{other_guardian.pk}',
        })
        self.assertEqual(PickupRecord.objects.count(), 0)

    def test_inactive_authorized_person_is_ignored(self):
        self.person.is_active = False
        self.person.save()
        self.client.post(self._url(), {
            'date': self.date,
            f'picker_{self.enrollment.pk}': f'person:{self.person.pk}',
        })
        self.assertEqual(PickupRecord.objects.count(), 0)

    def test_resubmitting_same_date_updates_not_duplicates(self):
        self.client.post(self._url(), {
            'date': self.date,
            f'picker_{self.enrollment.pk}': f'guardian:{self.guardian.pk}',
        })
        self.client.post(self._url(), {
            'date': self.date,
            f'picker_{self.enrollment.pk}': f'person:{self.person.pk}',
        })
        self.assertEqual(PickupRecord.objects.filter(date=self.date).count(), 1)
        pickup = PickupRecord.objects.get(enrollment=self.enrollment, date=self.date)
        self.assertEqual(pickup.authorized_person, self.person)
        self.assertIsNone(pickup.guardian)

    def test_take_logs_summary_audit_entry(self):
        self.client.post(self._url(), {
            'date': self.date,
            f'picker_{self.enrollment.pk}': f'guardian:{self.guardian.pk}',
        })
        logs = AuditLog.objects.filter(action=AuditLog.Action.UPDATE, model_name='pickuprecord')
        self.assertEqual(logs.count(), 1)
        self.assertIn('1 départ', logs.first().details)

    def test_future_date_falls_back_to_today(self):
        future = (timezone.localdate() + timedelta(days=5)).isoformat()
        response = self.client.get(f'{self._url()}?date={future}')
        self.assertEqual(response.context['date'], timezone.localdate())

    def test_get_includes_picker_options(self):
        response = self.client.get(self._url())
        row = response.context['rows'][0]
        self.assertIn((f'guardian:{self.guardian.pk}', str(self.guardian)), row['guardians'])
        self.assertIn((f'person:{self.person.pk}', str(self.person)), row['persons'])


class StudentPickupHistoryViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.student = make_student()
        self.other_student = make_student(last_name='Martin')
        self.enrollment = make_enrollment(student=self.student)
        self.other_enrollment = make_enrollment(student=self.other_student)
        self.guardian = make_guardian()

    def test_only_shows_requested_student(self):
        PickupRecord.objects.create(enrollment=self.enrollment, date='2026-01-15', guardian=self.guardian)
        other_guardian = make_guardian(last_name='Autre')
        PickupRecord.objects.create(enrollment=self.other_enrollment, date='2026-01-15', guardian=other_guardian)
        response = self.client.get(reverse('pickups:student-history', args=[self.student.pk]))
        self.assertEqual(len(response.context['pickups']), 1)
        self.assertEqual(response.context['pickups'][0].enrollment, self.enrollment)

    def test_ordered_by_date_descending(self):
        PickupRecord.objects.create(enrollment=self.enrollment, date='2026-01-10', guardian=self.guardian)
        PickupRecord.objects.create(enrollment=self.enrollment, date='2026-01-20', guardian=self.guardian)
        response = self.client.get(reverse('pickups:student-history', args=[self.student.pk]))
        dates = [p.date.isoformat() for p in response.context['pickups']]
        self.assertEqual(dates, ['2026-01-20', '2026-01-10'])
