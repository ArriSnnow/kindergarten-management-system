import itertools
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from academics.models import Class, Enrollment, SchoolYear
from attendance.models import Attendance
from audit.models import AuditLog
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


class AttendanceModelTests(TestCase):
    def test_unique_per_enrollment_date(self):
        enrollment = make_enrollment()
        Attendance.objects.create(enrollment=enrollment, date='2026-01-15')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(enrollment=enrollment, date='2026-01-15')

    def test_different_dates_allowed(self):
        enrollment = make_enrollment()
        Attendance.objects.create(enrollment=enrollment, date='2026-01-15')
        Attendance.objects.create(enrollment=enrollment, date='2026-01-16')
        self.assertEqual(Attendance.objects.count(), 2)

    def test_default_status_present(self):
        attendance = Attendance.objects.create(enrollment=make_enrollment(), date='2026-01-15')
        self.assertEqual(attendance.status, Attendance.Status.PRESENT)

    def test_clean_rejects_future_date(self):
        attendance = Attendance(enrollment=make_enrollment(), date=timezone.localdate() + timedelta(days=1))
        with self.assertRaises(ValidationError):
            attendance.clean()

    def test_clean_allows_today(self):
        attendance = Attendance(enrollment=make_enrollment(), date=timezone.localdate())
        attendance.clean()


class AttendanceAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.classe = make_class()
        self.student = make_student()

    def test_anonymous_redirected_from_take_view(self):
        response = self.client.get(reverse('attendance:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 302)

    def test_parent_forbidden_from_take_view(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('attendance:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 403)

    def test_parent_forbidden_from_history_view(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('attendance:student-history', args=[self.student.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed_take_view(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('attendance:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 200)


class AttendanceTakeFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.classe = make_class()
        self.enrollment = make_enrollment(school_year=self.classe.school_year, classe=self.classe)
        self.other_enrollment = make_enrollment(
            student=make_student(last_name='Martin'), school_year=self.classe.school_year, classe=self.classe,
        )
        self.date = '2026-01-15'

    def _url(self):
        return reverse('attendance:take', args=[self.classe.pk])

    def test_take_creates_records_for_roster(self):
        response = self.client.post(self._url(), {
            'date': self.date,
            f'status_{self.enrollment.pk}': Attendance.Status.PRESENT,
            f'status_{self.other_enrollment.pk}': Attendance.Status.ABSENT,
        })
        self.assertRedirects(
            response, f'{self._url()}?date={self.date}', fetch_redirect_response=False,
        )
        self.assertEqual(Attendance.objects.filter(date=self.date).count(), 2)
        self.assertEqual(
            Attendance.objects.get(enrollment=self.other_enrollment, date=self.date).status,
            Attendance.Status.ABSENT,
        )

    def test_resubmitting_same_date_updates_not_duplicates(self):
        self.client.post(self._url(), {
            'date': self.date,
            f'status_{self.enrollment.pk}': Attendance.Status.PRESENT,
            f'status_{self.other_enrollment.pk}': Attendance.Status.PRESENT,
        })
        self.client.post(self._url(), {
            'date': self.date,
            f'status_{self.enrollment.pk}': Attendance.Status.LATE,
            f'status_{self.other_enrollment.pk}': Attendance.Status.PRESENT,
        })
        self.assertEqual(Attendance.objects.filter(date=self.date).count(), 2)
        self.assertEqual(
            Attendance.objects.get(enrollment=self.enrollment, date=self.date).status, Attendance.Status.LATE,
        )

    def test_only_active_enrollments_included(self):
        withdrawn = make_enrollment(
            student=make_student(last_name='Petit'), school_year=self.classe.school_year, classe=self.classe,
            status=Enrollment.Status.WITHDRAWN,
        )
        response = self.client.get(self._url())
        enrollments_in_context = [row[0] for row in response.context['rows']]
        self.assertNotIn(withdrawn, enrollments_in_context)

    def test_empty_roster_shows_no_rows(self):
        empty_class = make_class(school_year=self.classe.school_year, name='Vide')
        response = self.client.get(reverse('attendance:take', args=[empty_class.pk]))
        self.assertEqual(list(response.context['rows']), [])

    def test_take_logs_single_summary_audit_entry(self):
        self.client.post(self._url(), {
            'date': self.date,
            f'status_{self.enrollment.pk}': Attendance.Status.PRESENT,
            f'status_{self.other_enrollment.pk}': Attendance.Status.ABSENT,
        })
        logs = AuditLog.objects.filter(action=AuditLog.Action.UPDATE, model_name='attendance')
        self.assertEqual(logs.count(), 1)
        self.assertIn('1 présent', logs.first().details)
        self.assertIn('1 absent', logs.first().details)

    def test_future_date_falls_back_to_today(self):
        future = (timezone.localdate() + timedelta(days=5)).isoformat()
        response = self.client.get(f'{self._url()}?date={future}')
        self.assertEqual(response.context['date'], timezone.localdate())


class StudentAttendanceHistoryViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.student = make_student()
        self.other_student = make_student(last_name='Martin')
        self.enrollment = make_enrollment(student=self.student)
        self.other_enrollment = make_enrollment(student=self.other_student)

    def test_only_shows_requested_student(self):
        Attendance.objects.create(enrollment=self.enrollment, date='2026-01-15')
        Attendance.objects.create(enrollment=self.other_enrollment, date='2026-01-15')
        response = self.client.get(reverse('attendance:student-history', args=[self.student.pk]))
        self.assertEqual(len(response.context['attendances']), 1)
        self.assertEqual(response.context['attendances'][0].enrollment, self.enrollment)

    def test_ordered_by_date_descending(self):
        Attendance.objects.create(enrollment=self.enrollment, date='2026-01-10')
        Attendance.objects.create(enrollment=self.enrollment, date='2026-01-20')
        response = self.client.get(reverse('attendance:student-history', args=[self.student.pk]))
        dates = [a.date.isoformat() for a in response.context['attendances']]
        self.assertEqual(dates, ['2026-01-20', '2026-01-10'])
