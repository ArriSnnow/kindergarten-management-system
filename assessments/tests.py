import itertools
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from academics.models import Class, Enrollment, SchoolYear
from assessments.models import Assessment
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


class AssessmentModelTests(TestCase):
    def test_unique_per_enrollment_domain_period(self):
        enrollment = make_enrollment()
        Assessment.objects.create(enrollment=enrollment, domain='Langage', period='Trimestre 1')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Assessment.objects.create(enrollment=enrollment, domain='Langage', period='Trimestre 1')

    def test_different_period_allowed(self):
        enrollment = make_enrollment()
        Assessment.objects.create(enrollment=enrollment, domain='Langage', period='Trimestre 1')
        Assessment.objects.create(enrollment=enrollment, domain='Langage', period='Trimestre 2')
        self.assertEqual(Assessment.objects.count(), 2)

    def test_negative_score_rejected_by_db(self):
        enrollment = make_enrollment()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Assessment.objects.create(
                    enrollment=enrollment, domain='Langage', period='Trimestre 1', score=Decimal('-1'),
                )

    def test_scale_and_score_both_optional(self):
        enrollment = make_enrollment()
        assessment = Assessment.objects.create(enrollment=enrollment, domain='Langage', period='Trimestre 1')
        self.assertEqual(assessment.scale, '')
        self.assertIsNone(assessment.score)

    def test_both_scale_and_score_can_be_set(self):
        enrollment = make_enrollment()
        assessment = Assessment.objects.create(
            enrollment=enrollment, domain='Langage', period='Trimestre 1',
            scale=Assessment.Scale.TRES_BIEN, score=Decimal('18'),
        )
        self.assertEqual(assessment.scale, Assessment.Scale.TRES_BIEN)
        self.assertEqual(assessment.score, Decimal('18'))


class AssessmentsAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.classe = make_class()
        self.student = make_student()

    def test_anonymous_redirected_from_take_view(self):
        response = self.client.get(reverse('assessments:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 302)

    def test_parent_forbidden_from_take_view(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('assessments:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 403)

    def test_parent_forbidden_from_history_view(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('assessments:student-history', args=[self.student.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed_take_view(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('assessments:take', args=[self.classe.pk]))
        self.assertEqual(response.status_code, 200)


class AssessmentTakeFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.classe = make_class()
        self.enrollment = make_enrollment(school_year=self.classe.school_year, classe=self.classe)
        self.other_enrollment = make_enrollment(
            student=make_student(last_name='Martin'), school_year=self.classe.school_year, classe=self.classe,
        )
        self.domain = 'Langage'
        self.period = 'Trimestre 1'

    def _url(self):
        return reverse('assessments:take', args=[self.classe.pk])

    def test_get_without_domain_period_shows_no_rows(self):
        response = self.client.get(self._url())
        self.assertEqual(response.context['rows'], [])

    def test_get_with_domain_period_shows_roster(self):
        response = self.client.get(self._url(), {'domain': self.domain, 'period': self.period})
        self.assertEqual(len(response.context['rows']), 2)

    def test_take_creates_records(self):
        response = self.client.post(self._url(), {
            'domain': self.domain, 'period': self.period,
            f'scale_{self.enrollment.pk}': Assessment.Scale.TRES_BIEN,
            f'score_{self.enrollment.pk}': '18',
            f'scale_{self.other_enrollment.pk}': Assessment.Scale.BIEN,
        })
        self.assertRedirects(
            response, f'{self._url()}?domain={self.domain}&period={self.period}', fetch_redirect_response=False,
        )
        self.assertEqual(Assessment.objects.filter(domain=self.domain, period=self.period).count(), 2)
        assessment = Assessment.objects.get(enrollment=self.enrollment, domain=self.domain, period=self.period)
        self.assertEqual(assessment.scale, Assessment.Scale.TRES_BIEN)
        self.assertEqual(assessment.score, Decimal('18'))

    def test_blank_row_creates_no_record(self):
        self.client.post(self._url(), {
            'domain': self.domain, 'period': self.period,
            f'scale_{self.enrollment.pk}': '',
            f'score_{self.enrollment.pk}': '',
            f'note_{self.enrollment.pk}': '',
        })
        self.assertEqual(Assessment.objects.count(), 0)

    def test_note_only_row_creates_record(self):
        self.client.post(self._url(), {
            'domain': self.domain, 'period': self.period,
            f'note_{self.enrollment.pk}': 'Progrès notable',
        })
        assessment = Assessment.objects.get(enrollment=self.enrollment)
        self.assertEqual(assessment.note, 'Progrès notable')

    def test_invalid_scale_ignored(self):
        self.client.post(self._url(), {
            'domain': self.domain, 'period': self.period,
            f'scale_{self.enrollment.pk}': 'NOT_A_CHOICE',
            f'score_{self.enrollment.pk}': '15',
        })
        assessment = Assessment.objects.get(enrollment=self.enrollment)
        self.assertEqual(assessment.scale, '')
        self.assertEqual(assessment.score, Decimal('15'))

    def test_resubmitting_updates_not_duplicates(self):
        self.client.post(self._url(), {
            'domain': self.domain, 'period': self.period,
            f'scale_{self.enrollment.pk}': Assessment.Scale.BIEN,
        })
        self.client.post(self._url(), {
            'domain': self.domain, 'period': self.period,
            f'scale_{self.enrollment.pk}': Assessment.Scale.EXCELLENT,
        })
        self.assertEqual(Assessment.objects.filter(enrollment=self.enrollment).count(), 1)
        assessment = Assessment.objects.get(enrollment=self.enrollment)
        self.assertEqual(assessment.scale, Assessment.Scale.EXCELLENT)

    def test_missing_domain_or_period_rejected(self):
        response = self.client.post(self._url(), {
            'domain': '', 'period': self.period,
            f'scale_{self.enrollment.pk}': Assessment.Scale.BIEN,
        })
        self.assertRedirects(response, self._url())
        self.assertEqual(Assessment.objects.count(), 0)

    def test_take_logs_summary_audit_entry(self):
        self.client.post(self._url(), {
            'domain': self.domain, 'period': self.period,
            f'scale_{self.enrollment.pk}': Assessment.Scale.BIEN,
        })
        logs = AuditLog.objects.filter(action=AuditLog.Action.UPDATE, model_name='assessment')
        self.assertEqual(logs.count(), 1)
        self.assertIn('1 évaluation', logs.first().details)


class StudentAssessmentHistoryViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.student = make_student()
        self.other_student = make_student(last_name='Martin')
        self.enrollment = make_enrollment(student=self.student)
        self.other_enrollment = make_enrollment(student=self.other_student)

    def test_only_shows_requested_student(self):
        Assessment.objects.create(enrollment=self.enrollment, domain='Langage', period='Trimestre 1')
        Assessment.objects.create(enrollment=self.other_enrollment, domain='Langage', period='Trimestre 1')
        response = self.client.get(reverse('assessments:student-history', args=[self.student.pk]))
        self.assertEqual(len(response.context['assessments']), 1)
        self.assertEqual(response.context['assessments'][0].enrollment, self.enrollment)
