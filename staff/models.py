from django.db import models


class Staff(models.Model):
    last_name = models.CharField('nom', max_length=100)
    first_name = models.CharField('prénom', max_length=100)
    phone = models.CharField('téléphone', max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name.upper()} {self.first_name}'
