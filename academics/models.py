from django.db import models, transaction

from staff.models import Staff
from students.models import RegistrationGrade, Student


class SchoolYear(models.Model):
    label = models.CharField('année scolaire', max_length=9, unique=True)
    start_date = models.DateField('date de début')
    end_date = models.DateField('date de fin')
    is_current = models.BooleanField('année courante', default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'année scolaire'
        verbose_name_plural = 'années scolaires'

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_current:
                SchoolYear.objects.exclude(pk=self.pk).filter(is_current=True).update(is_current=False)


class Class(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.PROTECT, related_name='classes')
    grade = models.CharField('niveau', max_length=2, choices=RegistrationGrade.choices)
    name = models.CharField('nom de la classe', max_length=20, blank=True)
    teacher = models.ForeignKey(
        Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes',
        verbose_name='enseignant',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['school_year', 'grade', 'name']
        verbose_name = 'classe'
        verbose_name_plural = 'classes'
        constraints = [
            models.UniqueConstraint(
                fields=['school_year', 'grade', 'name'], name='unique_class_per_year_grade_name',
            ),
        ]

    def __str__(self):
        label = self.get_grade_display()
        if self.name:
            label += f' {self.name}'
        return f'{label} ({self.school_year})'


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        WITHDRAWN = 'WITHDRAWN', 'Retirée'

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    school_year = models.ForeignKey(SchoolYear, on_delete=models.PROTECT, related_name='enrollments')
    grade = models.CharField('niveau', max_length=2, choices=RegistrationGrade.choices)
    classe = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments',
        verbose_name='classe',
    )
    status = models.CharField('statut', max_length=10, choices=Status.choices, default=Status.ACTIVE)
    withdrawn_at = models.DateTimeField('retirée le', null=True, blank=True)
    withdrawal_reason = models.CharField('motif de retrait', max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-school_year__start_date']
        verbose_name = 'inscription'
        verbose_name_plural = 'inscriptions'
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'school_year'], name='unique_enrollment_per_student_year',
            ),
        ]

    def __str__(self):
        return f'{self.student} — {self.school_year} ({self.get_grade_display()})'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE
