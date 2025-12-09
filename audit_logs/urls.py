from django.urls import path
from . import views

app_name = 'audit_logs'

urlpatterns = [
    path('', views.audit_logs_view, name='audit_logs'),
    path('export/', views.export_audit_logs, name='export'),

    # Admin usage analytics
    path('admin/analytics/', views.admin_usage_analytics_view, name='admin_analytics'),
    path('admin/analytics/export/', views.admin_usage_export_csv, name='admin_export_csv'),
    # API endpoint for front-end filtering / AJAX
    path('api/filter/', views.audit_logs_api, name='api_filter'),
]
