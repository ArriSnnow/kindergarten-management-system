from django import forms

from guardians.models import AuthorizedPickupPerson, Guardian, StudentGuardian


class _BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) \
                else 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            field.widget.attrs.setdefault('class', css_class)


class GuardianForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Guardian
        fields = ['last_name', 'first_name', 'phone', 'email', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class StudentGuardianForm(_BootstrapFormMixin, forms.ModelForm):
    guardian = forms.ModelChoiceField(label='Tuteur', queryset=Guardian.objects.filter(is_active=True))

    class Meta:
        model = StudentGuardian
        fields = ['guardian', 'relationship_type', 'is_primary_contact']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class AuthorizedPickupPersonForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AuthorizedPickupPerson
        fields = ['last_name', 'first_name', 'relationship', 'phone', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
