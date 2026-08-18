from django.urls import path

from pickups.views import PickupTakeView, StudentPickupHistoryView

app_name = 'pickups'

urlpatterns = [
    path('classes/<int:class_pk>/', PickupTakeView.as_view(), name='take'),
    path('eleves/<int:student_pk>/', StudentPickupHistoryView.as_view(), name='student-history'),
]
