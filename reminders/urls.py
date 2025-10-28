from django.urls import path
from . import views

# Namespace for reversing URLs like: url 'reminders:home'
app_name = "reminders"

urlpatterns = [
    # GET /reminders/ -> Reminders and Notifications page
    path("", views.reminders_page, name="home"),
]
