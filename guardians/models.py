from django.conf import settings
from django.db import models

from students.models import Student


class Guardian(models.Model):
    last_name = models.CharField('nom', max_length=100)
    first_name = models.CharField('prénom', max_length=100)
    phone = models.CharField('téléphone', max_length=30)
    email = models.EmailField('courriel', blank=True)
    address = models.CharField('adresse', max_length=255, blank=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guardian_profile',
        verbose_name='compte parent lié',
    )

    is_active = models.BooleanField('actif', default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name.upper()} {self.first_name}'


class StudentGuardian(models.Model):
    class RelationshipType(models.TextChoices):
        FATHER = 'PERE', 'Père'
        MOTHER = 'MERE', 'Mère'
        LEGAL_GUARDIAN = 'TUTEUR_LEGAL', 'Tuteur légal'
        OTHER = 'AUTRE', 'Autre'

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='guardian_links')
    guardian = models.ForeignKey(Guardian, on_delete=models.PROTECT, related_name='student_links')
    relationship_type = models.CharField(
        'lien de parenté', max_length=20, choices=RelationshipType.choices,
    )
    is_primary_contact = models.BooleanField('contact principal', default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary_contact', 'guardian__last_name']
        constraints = [
            models.UniqueConstraint(fields=['student', 'guardian'], name='unique_student_guardian'),
        ]

    def __str__(self):
        return f'{self.guardian} ({self.get_relationship_type_display()}) — {self.student}'


class AuthorizedPickupPerson(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='authorized_pickups')
    last_name = models.CharField('nom', max_length=100)
    first_name = models.CharField('prénom', max_length=100)
    relationship = models.CharField('lien avec l\'élève', max_length=100)
    phone = models.CharField('téléphone', max_length=30)
    notes = models.TextField('notes', blank=True)
    is_active = models.BooleanField('actif', default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name.upper()} {self.first_name} ({self.relationship})'
