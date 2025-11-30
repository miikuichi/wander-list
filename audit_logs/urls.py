from django.urls import path
from . import views

app_name = 'audit_logs'

urlpatterns = [
    path('', views.audit_logs_view, name='audit_logs'),
    path('export/', views.export_audit_logs, name='export'),
]
