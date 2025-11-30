# dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('admin-panel/', views.admin_dashboard_view, name='admin_dashboard'),
    path('settings/monthly-allowance/', views.update_monthly_allowance_view, name='update_monthly_allowance'),
]