from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.views.generic import TemplateView

from accounts.mixins import AdminRequiredMixin, ParentRequiredMixin

User = get_user_model()


class UserModelTests(TestCase):
    def test_default_role_is_parent(self):
        user = User.objects.create_user(username='parent1', password='pass12345')
        self.assertEqual(user.role, User.Role.PARENT)
        self.assertTrue(user.is_parent)
        self.assertFalse(user.is_admin)

    def test_explicit_admin_role(self):
        user = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.assertTrue(user.is_admin)
        self.assertFalse(user.is_parent)

    def test_superuser_forces_admin_role(self):
        user = User.objects.create_superuser(username='root', password='pass12345')
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_admin)


class _AdminOnlyView(AdminRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'


class _ParentOnlyView(ParentRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'


class RoleMixinTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pass12345', role=User.Role.ADMIN)
        self.parent = User.objects.create_user(username='parent1', password='pass12345', role=User.Role.PARENT)
        self.factory = RequestFactory()

    def _test_func_for(self, view_class, user):
        request = self.factory.get('/')
        request.user = user
        view = view_class()
        view.request = request
        return view.test_func()

    def test_admin_required_mixin_blocks_parent(self):
        self.assertFalse(self._test_func_for(_AdminOnlyView, self.parent))

    def test_admin_required_mixin_allows_admin(self):
        self.assertTrue(self._test_func_for(_AdminOnlyView, self.admin))

    def test_parent_required_mixin_blocks_admin(self):
        self.assertFalse(self._test_func_for(_ParentOnlyView, self.admin))

    def test_parent_required_mixin_allows_parent(self):
        self.assertTrue(self._test_func_for(_ParentOnlyView, self.parent))


class AuthFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='parent1', password='pass12345')

    def test_login_success_redirects_to_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'parent1',
            'password': 'pass12345',
        })
        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_login_failure_shows_error(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'parent1',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'incorrect')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_logout(self):
        self.client.login(username='parent1', password='pass12345')
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)
