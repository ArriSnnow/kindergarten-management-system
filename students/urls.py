from django.urls import path

from guardians.views import (
    AuthorizedPickupPersonCreateView,
    AuthorizedPickupPersonDeactivateView,
    AuthorizedPickupPersonReactivateView,
    AuthorizedPickupPersonUpdateView,
    StudentGuardianCreateView,
    StudentGuardianDeleteView,
)
from students.views import (
    StudentArchiveView,
    StudentCreateView,
    StudentDetailView,
    StudentListView,
    StudentReactivateView,
    StudentUpdateView,
)

app_name = 'students'

urlpatterns = [
    path('', StudentListView.as_view(), name='list'),
    path('ajouter/', StudentCreateView.as_view(), name='create'),
    path('<int:pk>/', StudentDetailView.as_view(), name='detail'),
    path('<int:pk>/modifier/', StudentUpdateView.as_view(), name='update'),
    path('<int:pk>/archiver/', StudentArchiveView.as_view(), name='archive'),
    path('<int:pk>/reactiver/', StudentReactivateView.as_view(), name='reactivate'),

    path('<int:student_pk>/tuteurs/ajouter/', StudentGuardianCreateView.as_view(), name='guardian-add'),
    path('<int:student_pk>/tuteurs/<int:link_pk>/retirer/', StudentGuardianDeleteView.as_view(),
         name='guardian-remove'),

    path('<int:student_pk>/personnes-autorisees/ajouter/', AuthorizedPickupPersonCreateView.as_view(),
         name='pickup-add'),
    path('<int:student_pk>/personnes-autorisees/<int:pk>/modifier/',
         AuthorizedPickupPersonUpdateView.as_view(), name='pickup-update'),
    path('<int:student_pk>/personnes-autorisees/<int:pk>/desactiver/',
         AuthorizedPickupPersonDeactivateView.as_view(), name='pickup-deactivate'),
    path('<int:student_pk>/personnes-autorisees/<int:pk>/reactiver/',
         AuthorizedPickupPersonReactivateView.as_view(), name='pickup-reactivate'),
]
