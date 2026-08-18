"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path

from config.views import HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('comptes/', include('accounts.urls')),
    path('eleves/', include('students.urls')),
    path('tuteurs/', include('guardians.urls')),
    path('personnel/', include('staff.urls')),
    path('academique/', include('academics.urls')),
    path('presences/', include('attendance.urls')),
    path('departs/', include('pickups.urls')),
    path('', HomeView.as_view(), name='home'),
]
