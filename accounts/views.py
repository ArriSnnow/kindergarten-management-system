from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView


class KindergartenLoginView(LoginView):
    template_name = 'accounts/login.html'


class KindergartenLogoutView(LogoutView):
    pass


class DashboardView(LoginRequiredMixin, TemplateView):
    """Placeholder post-login landing page, greets the user by role."""
    template_name = 'accounts/dashboard.html'
