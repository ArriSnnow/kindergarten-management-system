from django import forms

from students.models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'last_name', 'first_name', 'date_of_birth', 'gender', 'enrollment_date',
            'registration_grade', 'cabinet', 'drawer', 'position',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'enrollment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            del self.fields['registration_grade']
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs.setdefault('class', css_class)


class StudentArchiveForm(forms.Form):
    archive_reason = forms.CharField(
        label='Motif d\'archivage',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
