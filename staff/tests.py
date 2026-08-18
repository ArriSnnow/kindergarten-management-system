from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
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


class StaffModelTests(TestCase):
    def test_str_representation(self):
        staff = make_staff(last_name='girard', first_name='Nadia')
        self.assertEqual(str(staff), 'GIRARD Nadia')

    def test_phone_optional(self):
        staff = Staff.objects.create(last_name='Girard', first_name='Nadia')
        self.assertEqual(staff.phone, '')

    def test_default_is_active(self):
        staff = make_staff()
        self.assertTrue(staff.is_active)

    def test_position_and_hire_date_optional(self):
        staff = Staff.objects.create(last_name='Girard', first_name='Nadia')
        self.assertEqual(staff.position, '')
        self.assertIsNone(staff.hire_date)


class StaffAccessControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.staff = make_staff()

    def test_anonymous_redirected(self):
        response = self.client.get(reverse('staff:list'))
        self.assertEqual(response.status_code, 302)

    def test_parent_forbidden(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('staff:list'))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('staff:list'))
        self.assertEqual(response.status_code, 200)

    def test_parent_forbidden_from_detail(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.get(reverse('staff:detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_allowed_detail(self):
        self.client.login(username='admin1', password='pass12345')
        response = self.client.get(reverse('staff:detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)


class StaffCrudFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')

    def test_create_staff_logs_audit(self):
        response = self.client.post(reverse('staff:create'), {
            'last_name': 'Girard', 'first_name': 'Nadia', 'phone': '0600000000',
            'position': 'Enseignante', 'hire_date': '2026-01-05',
        })
        staff = Staff.objects.get(last_name='Girard')
        self.assertRedirects(response, reverse('staff:detail', args=[staff.pk]))
        self.assertEqual(staff.position, 'Enseignante')
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.CREATE, model_name='staff').exists(),
        )

    def test_update_staff(self):
        staff = make_staff()
        response = self.client.post(reverse('staff:update', args=[staff.pk]), {
            'last_name': 'Nouveaunom', 'first_name': staff.first_name, 'phone': staff.phone,
            'position': '', 'hire_date': '',
        })
        staff.refresh_from_db()
        self.assertRedirects(response, reverse('staff:detail', args=[staff.pk]))
        self.assertEqual(staff.last_name, 'Nouveaunom')

    def test_search_by_name(self):
        make_staff(last_name='Girard', first_name='Nadia')
        make_staff(last_name='Bernard', first_name='Tom')
        response = self.client.get(reverse('staff:list'), {'q': 'Girard'})
        self.assertContains(response, 'GIRARD')
        self.assertNotContains(response, 'BERNARD')


class StaffDeactivateReactivateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.client.login(username='admin1', password='pass12345')
        self.staff = make_staff()

    def test_deactivate(self):
        response = self.client.post(reverse('staff:deactivate', args=[self.staff.pk]))
        self.staff.refresh_from_db()
        self.assertRedirects(response, reverse('staff:detail', args=[self.staff.pk]))
        self.assertFalse(self.staff.is_active)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.DEACTIVATE, model_name='staff').exists(),
        )

    def test_reactivate(self):
        self.staff.is_active = False
        self.staff.save()
        response = self.client.post(reverse('staff:reactivate', args=[self.staff.pk]))
        self.staff.refresh_from_db()
        self.assertRedirects(response, reverse('staff:detail', args=[self.staff.pk]))
        self.assertTrue(self.staff.is_active)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.REACTIVATE, model_name='staff').exists(),
        )
