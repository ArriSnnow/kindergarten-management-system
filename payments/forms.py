from django import forms

from payments.models import Fee, Payment


class _BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) \
                else 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            field.widget.attrs.setdefault('class', css_class)


class FeeForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Fee
        fields = ['amount_due', 'note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class PaymentForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'date', 'method', 'note']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
