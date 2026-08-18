from django.urls import path

from staff.views import (
    StaffCreateView,
    StaffDeactivateView,
    StaffDetailView,
    StaffListView,
    StaffReactivateView,
    StaffUpdateView,
)

app_name = 'staff'

urlpatterns = [
    path('', StaffListView.as_view(), name='list'),
    path('ajouter/', StaffCreateView.as_view(), name='create'),
    path('<int:pk>/', StaffDetailView.as_view(), name='detail'),
    path('<int:pk>/modifier/', StaffUpdateView.as_view(), name='update'),
    path('<int:pk>/desactiver/', StaffDeactivateView.as_view(), name='deactivate'),
    path('<int:pk>/reactiver/', StaffReactivateView.as_view(), name='reactivate'),
]
