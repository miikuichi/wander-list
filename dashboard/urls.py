# dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('settings/monthly-allowance/', views.update_monthly_allowance_view, name='update_monthly_allowance'),
    path('settings/cache/', views.cache_settings_view, name='cache_settings'),
]