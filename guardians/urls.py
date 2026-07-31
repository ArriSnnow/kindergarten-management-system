from django.urls import path

from guardians.views import (
    GuardianCreateView,
    GuardianDeactivateView,
    GuardianDetailView,
    GuardianListView,
    GuardianReactivateView,
    GuardianUpdateView,
)

app_name = 'guardians'

urlpatterns = [
    path('', GuardianListView.as_view(), name='list'),
    path('ajouter/', GuardianCreateView.as_view(), name='create'),
    path('<int:pk>/', GuardianDetailView.as_view(), name='detail'),
    path('<int:pk>/modifier/', GuardianUpdateView.as_view(), name='update'),
    path('<int:pk>/desactiver/', GuardianDeactivateView.as_view(), name='deactivate'),
    path('<int:pk>/reactiver/', GuardianReactivateView.as_view(), name='reactivate'),
]
