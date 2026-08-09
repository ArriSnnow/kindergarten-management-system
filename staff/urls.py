from django.urls import path

from staff.views import StaffCreateView, StaffListView, StaffUpdateView

app_name = 'staff'

urlpatterns = [
    path('', StaffListView.as_view(), name='list'),
    path('ajouter/', StaffCreateView.as_view(), name='create'),
    path('<int:pk>/modifier/', StaffUpdateView.as_view(), name='update'),
]
