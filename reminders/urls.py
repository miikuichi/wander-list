from django.urls import path
from . import views

# Namespace for reversing URLs like: url 'reminders:home'
app_name = "reminders"

urlpatterns = [
    # GET /reminders/ -> Reminders and Notifications page
    path("", views.reminders_page, name="home"),
    path('delete/<int:reminder_id>/', views.delete_reminder, name='delete_reminder'),
    path('edit/<int:reminder_id>/', views.edit_reminder, name='edit_reminder'),
]
