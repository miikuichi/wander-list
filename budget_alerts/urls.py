from django.urls import path
from . import views

app_name = 'budget_alerts'

urlpatterns = [
    path("", views.alerts_page, name="alerts_page"),
    path("edit/<int:id>/", views.edit_alert, name="edit_alert"),
    path("delete/<int:id>/", views.delete_alert, name="delete_alert"),
    path("analysis/", views.budget_analysis_view, name="analysis"),
    path("api/predictions/", views.budget_predictions_api, name="predictions_api"),
    path("snooze/<int:alert_id>/", views.snooze_alert_view, name="snooze_alert"),
    path("unsnooze/<int:alert_id>/", views.unsnooze_alert_view, name="unsnooze_alert"),
    path("history/", views.alert_history_view, name="alert_history"),
]
