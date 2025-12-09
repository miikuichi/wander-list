# audit_logs/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

from .models import AuditLog


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    print("LOGIN SIGNAL FIRED FOR:", user)  # debug
    AuditLog.objects.create(
        user=user,
        action_type="LOGIN",
        resource_type="user",
        ip_address=request.META.get("REMOTE_ADDR", ""),
        timestamp=timezone.now(),
    )
