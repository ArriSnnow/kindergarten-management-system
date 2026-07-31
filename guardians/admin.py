from django.contrib import admin

from guardians.models import AuthorizedPickupPerson, Guardian, StudentGuardian


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'phone', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('last_name', 'first_name', 'email', 'phone')


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    list_display = ('student', 'guardian', 'relationship_type', 'is_primary_contact')
    list_filter = ('relationship_type', 'is_primary_contact')


@admin.register(AuthorizedPickupPerson)
class AuthorizedPickupPersonAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'student', 'relationship', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('last_name', 'first_name')
