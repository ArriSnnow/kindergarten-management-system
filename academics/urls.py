from django.urls import path

from academics.views import (
    ClassCreateView,
    ClassDetailView,
    ClassListView,
    ClassUpdateView,
    SchoolYearCreateView,
    SchoolYearListView,
    SchoolYearSetCurrentView,
    SchoolYearUpdateView,
)

app_name = 'academics'

urlpatterns = [
    path('annees/', SchoolYearListView.as_view(), name='schoolyear-list'),
    path('annees/ajouter/', SchoolYearCreateView.as_view(), name='schoolyear-create'),
    path('annees/<int:pk>/modifier/', SchoolYearUpdateView.as_view(), name='schoolyear-update'),
    path('annees/<int:pk>/definir-courante/', SchoolYearSetCurrentView.as_view(), name='schoolyear-set-current'),

    path('classes/', ClassListView.as_view(), name='class-list'),
    path('classes/ajouter/', ClassCreateView.as_view(), name='class-create'),
    path('classes/<int:pk>/', ClassDetailView.as_view(), name='class-detail'),
    path('classes/<int:pk>/modifier/', ClassUpdateView.as_view(), name='class-update'),
]
