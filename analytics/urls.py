"""
URL configuration for analytics app.
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Main analytics dashboard
    path('', views.analytics_dashboard, name='dashboard'),
    
    # API endpoints for chart data
    path('api/daily-spending/', views.api_daily_spending, name='api_daily_spending'),
    path('api/category-breakdown/', views.api_category_breakdown, name='api_category_breakdown'),
    path('api/weekly-comparison/', views.api_weekly_comparison, name='api_weekly_comparison'),
    path('api/monthly-trends/', views.api_monthly_trends, name='api_monthly_trends'),
    path('api/hourly-patterns/', views.api_hourly_patterns, name='api_hourly_patterns'),
    path('export-csv/', views.export_visual_report_csv, name='user_csv_export'),
]