from django import forms


class _BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) \
                else 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            field.widget.attrs.setdefault('class', css_class)


class AttendanceDateForm(_BootstrapFormMixin, forms.Form):
    date = forms.DateField(label='Date', widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
