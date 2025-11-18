from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_dashboard, name='dashboard'),
    path('mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_read'),
    path('preferences/', views.notification_preferences, name='preferences'),
    path('api/unread-count/', views.get_unread_count, name='unread_count'),
    path('api/recent/', views.get_recent_notifications, name='recent_notifications'),
    path('api/send-test-email/', views.send_test_email, name='send_test_email'),
]
