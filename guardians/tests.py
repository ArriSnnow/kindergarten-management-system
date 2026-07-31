from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from guardians.models import AuthorizedPickupPerson, Guardian, StudentGuardian
from students.models import Student

User = get_user_model()


def make_student(**kwargs):
    defaults = {
        'last_name': 'Dupont',
        'first_name': 'Léa',
        'date_of_birth': '2021-03-10',
        'gender': Student.Gender.GIRL,
        'enrollment_date': '2024-09-01',
    }
    defaults.update(kwargs)
    return Student.objects.create(**defaults)


def make_guardian(**kwargs):
    defaults = {
        'last_name': 'Petit',
        'first_name': 'Claire',
        'phone': '0600000000',
    }
    defaults.update(kwargs)
    return Guardian.objects.create(**defaults)


class GuardianModelTests(TestCase):
    def test_default_is_active(self):
        guardian = make_guardian()
        self.assertTrue(guardian.is_active)

    def test_str_representation(self):
        guardian = make_guardian(last_name='petit', first_name='Claire')
        self.assertEqual(str(guardian), 'PETIT Claire')

    def test_student_guardian_unique_together(self):
        student = make_student()
        guardian = make_guardian()
        StudentGuardian.objects.create(
            student=student, guardian=guardian, relationship_type=StudentGuardian.RelationshipType.MOTHER,
        )
        with self.assertRaises(Exception):
            StudentGuardian.objects.create(
                student=student, guardian=guardian,
                relationship_type=StudentGuardian.RelationshipType.OTHER,
            )

    def test_guardian_protected_from_deletion_when_linked(self):
        student = make_student()
        guardian = make_guardian()
        StudentGuardian.objects.create(
            student=student, guardian=guardian, relationship_type=StudentGuardian.RelationshipType.MOTHER,
        )
        with self.assertRaises(ProtectedError):
            guardian.delete()


class GuardianAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.guardian = make_guardian()

    def test_anonymous_redirected(self):
        response = self.client.get(reverse('guardians:list'))
        self.assertEqual(response.status_code, 302)

    def test_parent_forbidden(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('guardians:list'))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('guardians:list'))
        self.assertEqual(response.status_code, 200)


class GuardianCrudFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')

    def test_create_guardian_logs_audit(self):
        response = self.client.post(reverse('guardians:create'), {
            'last_name': 'Petit',
            'first_name': 'Claire',
            'phone': '0600000000',
            'email': '',
            'address': '',
        })
        guardian = Guardian.objects.get(last_name='Petit')
        self.assertRedirects(response, reverse('guardians:detail', args=[guardian.pk]))
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.CREATE, model_name='guardian').exists(),
        )

    def test_deactivate_and_reactivate_flow(self):
        guardian = make_guardian()
        response = self.client.post(reverse('guardians:deactivate', args=[guardian.pk]))
        guardian.refresh_from_db()
        self.assertRedirects(response, reverse('guardians:detail', args=[guardian.pk]))
        self.assertFalse(guardian.is_active)

        response = self.client.post(reverse('guardians:reactivate', args=[guardian.pk]))
        guardian.refresh_from_db()
        self.assertRedirects(response, reverse('guardians:detail', args=[guardian.pk]))
        self.assertTrue(guardian.is_active)

    def test_link_guardian_to_student(self):
        student = make_student()
        guardian = make_guardian()
        response = self.client.post(reverse('students:guardian-add', args=[student.pk]), {
            'guardian': guardian.pk,
            'relationship_type': StudentGuardian.RelationshipType.MOTHER,
            'is_primary_contact': True,
        })
        self.assertRedirects(response, reverse('students:detail', args=[student.pk]))
        self.assertTrue(StudentGuardian.objects.filter(student=student, guardian=guardian).exists())

    def test_remove_guardian_link(self):
        student = make_student()
        guardian = make_guardian()
        link = StudentGuardian.objects.create(
            student=student, guardian=guardian, relationship_type=StudentGuardian.RelationshipType.FATHER,
        )
        response = self.client.post(reverse('students:guardian-remove', args=[student.pk, link.pk]))
        self.assertRedirects(response, reverse('students:detail', args=[student.pk]))
        self.assertFalse(StudentGuardian.objects.filter(pk=link.pk).exists())

    def test_inactive_guardian_not_offered_when_linking(self):
        guardian = make_guardian(is_active=False)
        student = make_student()
        response = self.client.get(reverse('students:guardian-add', args=[student.pk]))
        self.assertNotContains(response, str(guardian))


class AuthorizedPickupPersonTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.student = make_student()

    def test_create_pickup_person(self):
        response = self.client.post(reverse('students:pickup-add', args=[self.student.pk]), {
            'last_name': 'Grand',
            'first_name': 'Mère',
            'relationship': 'Grand-mère',
            'phone': '0600000001',
            'notes': '',
        })
        self.assertRedirects(response, reverse('students:detail', args=[self.student.pk]))
        self.assertTrue(AuthorizedPickupPerson.objects.filter(student=self.student).exists())

    def test_deactivate_and_reactivate_pickup_person(self):
        person = AuthorizedPickupPerson.objects.create(
            student=self.student, last_name='Grand', first_name='Mère',
            relationship='Grand-mère', phone='0600000001',
        )
        response = self.client.post(
            reverse('students:pickup-deactivate', args=[self.student.pk, person.pk]),
        )
        person.refresh_from_db()
        self.assertRedirects(response, reverse('students:detail', args=[self.student.pk]))
        self.assertFalse(person.is_active)

        response = self.client.post(
            reverse('students:pickup-reactivate', args=[self.student.pk, person.pk]),
        )
        person.refresh_from_db()
        self.assertRedirects(response, reverse('students:detail', args=[self.student.pk]))
        self.assertTrue(person.is_active)
