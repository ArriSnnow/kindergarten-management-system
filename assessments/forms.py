from django import forms


class _BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) \
                else 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            field.widget.attrs.setdefault('class', css_class)


class AssessmentFilterForm(_BootstrapFormMixin, forms.Form):
    domain = forms.CharField(label='Domaine', max_length=100)
    period = forms.CharField(label='Période', max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
