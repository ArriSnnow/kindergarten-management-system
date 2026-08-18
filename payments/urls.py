from django.urls import path

from payments.views import FeeDetailView, FeeSetView, PaymentCreateView, PaymentVoidView

app_name = 'payments'

urlpatterns = [
    path('inscriptions/<int:enrollment_pk>/', FeeDetailView.as_view(), name='fee-detail'),
    path('inscriptions/<int:enrollment_pk>/definir/', FeeSetView.as_view(), name='fee-set'),
    path('inscriptions/<int:enrollment_pk>/paiements/ajouter/', PaymentCreateView.as_view(), name='payment-add'),
    path('inscriptions/<int:enrollment_pk>/paiements/<int:pk>/annuler/', PaymentVoidView.as_view(),
         name='payment-void'),
]
