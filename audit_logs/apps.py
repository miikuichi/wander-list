# audit_logs/apps.py
from django.apps import AppConfig

class AuditLogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit_logs"   # must match your app folder name

    def ready(self):
        import audit_logs.signals  # noqa
