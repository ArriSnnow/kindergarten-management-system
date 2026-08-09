from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from students.models import FileNumberSequence, Student

User = get_user_model()


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


class StudentModelTests(TestCase):
    def test_default_status_is_active(self):
        student = make_student()
        self.assertEqual(student.status, Student.Status.ACTIVE)
        self.assertFalse(student.is_archived)

    def test_str_representation(self):
        student = make_student(last_name='dupont', first_name='Léa')
        self.assertEqual(str(student), 'DUPONT Léa')

    def test_ordering_by_name(self):
        make_student(last_name='Zed', first_name='A')
        make_student(last_name='Abel', first_name='B')
        names = list(Student.objects.values_list('last_name', flat=True))
        self.assertEqual(names, ['Abel', 'Zed'])


class FileNumberGenerationTests(TestCase):
    def test_file_number_format(self):
        student = make_student(enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.PS)
        self.assertEqual(student.file_number, '2024-PS-001')

    def test_file_numbers_sequential_within_same_year_and_grade(self):
        first = make_student(enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.MS)
        second = make_student(
            last_name='Bernard', first_name='Tom',
            enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.MS,
        )
        self.assertEqual(first.file_number, '2024-MS-001')
        self.assertEqual(second.file_number, '2024-MS-002')

    def test_file_numbers_independent_per_grade(self):
        ps_student = make_student(enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.PS)
        gs_student = make_student(
            last_name='Bernard', first_name='Tom',
            enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.GS,
        )
        self.assertEqual(ps_student.file_number, '2024-PS-001')
        self.assertEqual(gs_student.file_number, '2024-GS-001')

    def test_file_numbers_independent_per_year(self):
        first = make_student(enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.PS)
        second = make_student(
            last_name='Bernard', first_name='Tom',
            enrollment_date='2025-09-01', registration_grade=Student.RegistrationGrade.PS,
        )
        self.assertEqual(first.file_number, '2024-PS-001')
        self.assertEqual(second.file_number, '2025-PS-001')

    def test_file_number_immutable_on_update(self):
        student = make_student(enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.PS)
        original_number = student.file_number
        student.last_name = 'Nouveaunom'
        student.save()
        student.refresh_from_db()
        self.assertEqual(student.file_number, original_number)

    def test_registration_grade_choice_does_not_affect_other_sequences_after_update(self):
        student = make_student(enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.PS)
        student.registration_grade = Student.RegistrationGrade.GS
        student.save()
        student.refresh_from_db()
        self.assertEqual(student.file_number, '2024-PS-001')

    def test_sequence_exhaustion_raises(self):
        FileNumberSequence.objects.create(year=2024, grade=Student.RegistrationGrade.PS, last_number=999)
        with self.assertRaises(ValueError):
            make_student(enrollment_date='2024-09-01', registration_grade=Student.RegistrationGrade.PS)

    def test_physical_location_fields_optional(self):
        student = make_student()
        self.assertEqual(student.cabinet, '')
        self.assertEqual(student.drawer, '')
        self.assertEqual(student.position, '')

    def test_physical_location_fields_can_be_set(self):
        student = make_student(cabinet='A', drawer='2', position='Gauche')
        self.assertEqual(student.cabinet, 'A')
        self.assertEqual(student.drawer, '2')
        self.assertEqual(student.position, 'Gauche')


class StudentAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.student = make_student()

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('students:list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_parent_forbidden(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('students:list'))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('students:list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_view_detail(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('students:detail', args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)


class StudentCrudFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')

    def test_create_student_logs_audit(self):
        response = self.client.post(reverse('students:create'), {
            'last_name': 'Martin',
            'first_name': 'Noah',
            'date_of_birth': '2020-05-01',
            'gender': Student.Gender.BOY,
            'enrollment_date': '2024-09-01',
            'registration_grade': Student.RegistrationGrade.PS,
        })
        student = Student.objects.get(last_name='Martin')
        self.assertRedirects(response, reverse('students:detail', args=[student.pk]))
        self.assertEqual(student.file_number, '2024-PS-001')
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.CREATE, model_name='student').exists(),
        )

    def test_update_student(self):
        student = make_student()
        response = self.client.post(reverse('students:update', args=[student.pk]), {
            'last_name': 'Nouveaunom',
            'first_name': student.first_name,
            'date_of_birth': student.date_of_birth,
            'gender': student.gender,
            'enrollment_date': student.enrollment_date,
        })
        student.refresh_from_db()
        self.assertRedirects(response, reverse('students:detail', args=[student.pk]))
        self.assertEqual(student.last_name, 'Nouveaunom')

    def test_archive_requires_reason(self):
        student = make_student()
        response = self.client.post(reverse('students:archive', args=[student.pk]), {})
        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertFalse(student.is_archived)

    def test_archive_and_reactivate_flow(self):
        student = make_student()
        response = self.client.post(reverse('students:archive', args=[student.pk]), {
            'archive_reason': 'Départ de la famille',
        })
        student.refresh_from_db()
        self.assertRedirects(response, reverse('students:detail', args=[student.pk]))
        self.assertTrue(student.is_archived)
        self.assertIsNotNone(student.archived_at)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.ARCHIVE, object_id=str(student.pk)).exists(),
        )

        response = self.client.post(reverse('students:reactivate', args=[student.pk]))
        student.refresh_from_db()
        self.assertRedirects(response, reverse('students:detail', args=[student.pk]))
        self.assertFalse(student.is_archived)
        self.assertIsNone(student.archived_at)

    def test_student_never_hard_deleted(self):
        student = make_student()
        self.client.post(reverse('students:archive', args=[student.pk]), {'archive_reason': 'Test'})
        self.assertTrue(Student.objects.filter(pk=student.pk).exists())

    def test_search_by_name(self):
        make_student(last_name='Dupont', first_name='Léa')
        make_student(last_name='Bernard', first_name='Tom')
        response = self.client.get(reverse('students:list'), {'q': 'Dupont'})
        self.assertContains(response, 'DUPONT')
        self.assertNotContains(response, 'BERNARD')
