from django.db import models, transaction
from django.utils.dateparse import parse_date


class RegistrationGrade(models.TextChoices):
    PS = 'PS', 'Petite Section'
    MS = 'MS', 'Moyenne Section'
    GS = 'GS', 'Grande Section'


class FileNumberSequence(models.Model):
    """Tracks the next available sequential number for a given (year, grade) pair."""

    year = models.PositiveIntegerField('année')
    grade = models.CharField('niveau', max_length=2, choices=RegistrationGrade.choices)
    last_number = models.PositiveIntegerField('dernier numéro', default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['year', 'grade'], name='unique_file_number_sequence'),
        ]
        verbose_name = 'séquence de numéro de dossier'
        verbose_name_plural = 'séquences de numéro de dossier'

    def __str__(self):
        return f'{self.year}-{self.grade}: {self.last_number}'


class Student(models.Model):
    RegistrationGrade = RegistrationGrade

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Actif'
        ARCHIVED = 'ARCHIVED', 'Archivé'

    class Gender(models.TextChoices):
        BOY = 'M', 'Garçon'
        GIRL = 'F', 'Fille'

    last_name = models.CharField('nom', max_length=100)
    first_name = models.CharField('prénom', max_length=100)
    date_of_birth = models.DateField('date de naissance')
    gender = models.CharField('sexe', max_length=1, choices=Gender.choices)
    enrollment_date = models.DateField('date d\'inscription')
    registration_grade = models.CharField(
        'niveau à l\'inscription', max_length=2, choices=RegistrationGrade.choices,
    )

    file_number = models.CharField(
        'numéro de dossier', max_length=12, unique=True, blank=True, editable=False,
    )
    cabinet = models.CharField('armoire', max_length=50, blank=True)
    drawer = models.CharField('tiroir', max_length=50, blank=True)
    position = models.CharField('position', max_length=50, blank=True)

    status = models.CharField(
        'statut', max_length=10, choices=Status.choices, default=Status.ACTIVE,
    )
    archived_at = models.DateTimeField('archivé le', null=True, blank=True)
    archive_reason = models.CharField('motif d\'archivage', max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name.upper()} {self.first_name}'

    @property
    def is_archived(self):
        return self.status == self.Status.ARCHIVED

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating and not self.file_number:
            self.file_number = self._generate_file_number()
            super().save(update_fields=['file_number'])

    def _generate_file_number(self):
        enrollment_date = self.enrollment_date
        if isinstance(enrollment_date, str):
            enrollment_date = parse_date(enrollment_date)
        with transaction.atomic():
            sequence, _ = FileNumberSequence.objects.select_for_update().get_or_create(
                year=enrollment_date.year, grade=self.registration_grade,
            )
            if sequence.last_number >= 999:
                raise ValueError(
                    f'Séquence de numéros de dossier épuisée pour {sequence.year}-{sequence.grade}.'
                )
            sequence.last_number += 1
            sequence.save(update_fields=['last_number'])
            return f'{sequence.year}-{sequence.grade}-{sequence.last_number:03d}'
