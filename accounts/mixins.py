from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts a view to authenticated users with the ADMIN role."""

    def test_func(self):
        return self.request.user.is_admin


class ParentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts a view to authenticated users with the PARENT role."""

    def test_func(self):
        return self.request.user.is_parent
