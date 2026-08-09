from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from academics.models import Class, Enrollment, SchoolYear
from audit.models import AuditLog
from staff.models import Staff
from students.models import Student

User = get_user_model()


def make_school_year(**kwargs):
    defaults = {
        'label': '2026-2027',
        'start_date': '2026-09-01',
        'end_date': '2027-07-01',
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


def make_class(**kwargs):
    defaults = {
        'school_year': make_school_year(),
        'grade': Student.RegistrationGrade.PS,
    }
    defaults.update(kwargs)
    return Class.objects.create(**defaults)


class SchoolYearModelTests(TestCase):
    def test_only_one_current_year_at_a_time(self):
        first = make_school_year(label='2025-2026', start_date='2025-09-01', end_date='2026-07-01', is_current=True)
        second = make_school_year(label='2026-2027', start_date='2026-09-01', end_date='2027-07-01', is_current=True)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)

    def test_label_unique(self):
        make_school_year(label='2026-2027')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_school_year(label='2026-2027', start_date='2026-09-02')

    def test_str_representation(self):
        year = make_school_year(label='2026-2027')
        self.assertEqual(str(year), '2026-2027')


class ClassModelTests(TestCase):
    def test_unique_per_year_grade_name(self):
        year = make_school_year()
        Class.objects.create(school_year=year, grade=Student.RegistrationGrade.PS, name='A')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Class.objects.create(school_year=year, grade=Student.RegistrationGrade.PS, name='A')

    def test_different_names_allowed_same_year_grade(self):
        year = make_school_year()
        Class.objects.create(school_year=year, grade=Student.RegistrationGrade.PS, name='A')
        Class.objects.create(school_year=year, grade=Student.RegistrationGrade.PS, name='B')
        self.assertEqual(Class.objects.count(), 2)

    def test_teacher_optional(self):
        classe = make_class()
        self.assertIsNone(classe.teacher)

    def test_teacher_assignment(self):
        teacher = Staff.objects.create(last_name='Girard', first_name='Nadia')
        classe = make_class(teacher=teacher)
        self.assertEqual(classe.teacher, teacher)


class EnrollmentModelTests(TestCase):
    def test_unique_per_student_year(self):
        student = make_student()
        year = make_school_year()
        Enrollment.objects.create(student=student, school_year=year, grade=Student.RegistrationGrade.PS)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Enrollment.objects.create(student=student, school_year=year, grade=Student.RegistrationGrade.PS)

    def test_second_year_enrollment_allowed(self):
        student = make_student()
        year1 = make_school_year(label='2025-2026', start_date='2025-09-01', end_date='2026-07-01')
        year2 = make_school_year(label='2026-2027', start_date='2026-09-01', end_date='2027-07-01')
        Enrollment.objects.create(student=student, school_year=year1, grade=Student.RegistrationGrade.PS)
        Enrollment.objects.create(student=student, school_year=year2, grade=Student.RegistrationGrade.MS)
        self.assertEqual(student.enrollments.count(), 2)

    def test_default_status_active(self):
        enrollment = Enrollment.objects.create(
            student=make_student(), school_year=make_school_year(), grade=Student.RegistrationGrade.PS,
        )
        self.assertTrue(enrollment.is_active)


class StudentCurrentEnrollmentTests(TestCase):
    def test_none_when_not_enrolled(self):
        student = make_student()
        self.assertIsNone(student.current_enrollment)

    def test_returns_enrollment_for_current_year(self):
        student = make_student()
        old_year = make_school_year(label='2025-2026', start_date='2025-09-01', end_date='2026-07-01')
        current_year = make_school_year(
            label='2026-2027', start_date='2026-09-01', end_date='2027-07-01', is_current=True,
        )
        Enrollment.objects.create(student=student, school_year=old_year, grade=Student.RegistrationGrade.PS)
        current = Enrollment.objects.create(
            student=student, school_year=current_year, grade=Student.RegistrationGrade.MS,
        )
        self.assertEqual(student.current_enrollment, current)


class AcademicsAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)

    def test_anonymous_redirected_from_schoolyear_list(self):
        response = self.client.get(reverse('academics:schoolyear-list'))
        self.assertEqual(response.status_code, 302)

    def test_parent_forbidden_from_class_list(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('academics:class-list'))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed_schoolyear_list(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('academics:schoolyear-list'))
        self.assertEqual(response.status_code, 200)


class EnrollmentFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.student = make_student()
        self.year = make_school_year(is_current=True)

    def test_create_enrollment_logs_audit(self):
        response = self.client.post(reverse('students:enrollment-add', args=[self.student.pk]), {
            'school_year': self.year.pk,
            'grade': Student.RegistrationGrade.PS,
        })
        enrollment = Enrollment.objects.get(student=self.student)
        self.assertRedirects(response, reverse('students:detail', args=[self.student.pk]))
        self.assertEqual(enrollment.school_year, self.year)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.CREATE, model_name='enrollment').exists(),
        )

    def test_withdraw_requires_reason(self):
        enrollment = Enrollment.objects.create(
            student=self.student, school_year=self.year, grade=Student.RegistrationGrade.PS,
        )
        response = self.client.post(
            reverse('students:enrollment-withdraw', args=[self.student.pk, enrollment.pk]), {},
        )
        self.assertEqual(response.status_code, 200)
        enrollment.refresh_from_db()
        self.assertTrue(enrollment.is_active)

    def test_withdraw_flow(self):
        enrollment = Enrollment.objects.create(
            student=self.student, school_year=self.year, grade=Student.RegistrationGrade.PS,
        )
        response = self.client.post(
            reverse('students:enrollment-withdraw', args=[self.student.pk, enrollment.pk]),
            {'withdrawal_reason': 'Déménagement'},
        )
        self.assertRedirects(response, reverse('students:detail', args=[self.student.pk]))
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.Status.WITHDRAWN)
        self.assertIsNotNone(enrollment.withdrawn_at)
        self.assertEqual(enrollment.withdrawal_reason, 'Déménagement')

    def test_enrollment_never_hard_deleted_on_withdraw(self):
        enrollment = Enrollment.objects.create(
            student=self.student, school_year=self.year, grade=Student.RegistrationGrade.PS,
        )
        self.client.post(
            reverse('students:enrollment-withdraw', args=[self.student.pk, enrollment.pk]),
            {'withdrawal_reason': 'Déménagement'},
        )
        self.assertTrue(Enrollment.objects.filter(pk=enrollment.pk).exists())
