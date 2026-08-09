from django import forms

from academics.models import Class, Enrollment, SchoolYear


class _BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) \
                else 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            field.widget.attrs.setdefault('class', css_class)


class SchoolYearForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SchoolYear
        fields = ['label', 'start_date', 'end_date', 'is_current']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class ClassForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Class
        fields = ['school_year', 'grade', 'name', 'teacher']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class EnrollmentForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['school_year', 'grade', 'classe']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classe'].required = False
        self.fields['classe'].queryset = Class.objects.select_related('school_year')
        self._apply_bootstrap()


class EnrollmentWithdrawForm(_BootstrapFormMixin, forms.Form):
    withdrawal_reason = forms.CharField(
        label='Motif de retrait',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
