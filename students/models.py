from django.db import models


class Student(models.Model):
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
