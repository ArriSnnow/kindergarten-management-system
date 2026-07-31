from django.contrib.auth import get_user_model
from django.test import TestCase

from audit.models import AuditLog
from audit.utils import log_action
from students.models import Student

User = get_user_model()


class LogActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.student = Student.objects.create(
            last_name='Dupont', first_name='Léa', date_of_birth='2021-03-10',
            gender=Student.Gender.GIRL, enrollment_date='2024-09-01',
        )

    def test_log_action_records_entry(self):
        log_action(self.admin, AuditLog.Action.CREATE, self.student, details='test')
        entry = AuditLog.objects.get()
        self.assertEqual(entry.actor, self.admin)
        self.assertEqual(entry.action, AuditLog.Action.CREATE)
        self.assertEqual(entry.model_name, 'student')
        self.assertEqual(entry.object_id, str(self.student.pk))
        self.assertEqual(entry.details, 'test')

    def test_log_action_with_anonymous_actor(self):
        from django.contrib.auth.models import AnonymousUser
        log_action(AnonymousUser(), AuditLog.Action.CREATE, self.student)
        entry = AuditLog.objects.get()
        self.assertIsNone(entry.actor)


class AuditLogAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='root', password='pass12345')
        self.client.login(username='root', password='pass12345')

    def test_audit_log_is_read_only_in_admin(self):
        response = self.client.get('/admin/audit/auditlog/add/')
        self.assertEqual(response.status_code, 403)
