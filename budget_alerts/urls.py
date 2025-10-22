from django.urls import path
from . import views

urlpatterns = [
    path("", views.alerts_page, name="alerts_page"),
    path("edit/<int:id>/", views.edit_alert, name="edit_alert"),  # Edit route
    path("delete/<int:id>/", views.delete_alert, name="delete_alert"),  # Delete route
]
