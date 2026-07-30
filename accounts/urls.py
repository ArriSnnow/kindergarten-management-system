from django.urls import path

from accounts.views import DashboardView, KindergartenLoginView, KindergartenLogoutView

app_name = 'accounts'

urlpatterns = [
    path('connexion/', KindergartenLoginView.as_view(), name='login'),
    path('deconnexion/', KindergartenLogoutView.as_view(), name='logout'),
    path('tableau-de-bord/', DashboardView.as_view(), name='dashboard'),
]
