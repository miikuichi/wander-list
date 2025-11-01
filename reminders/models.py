from django.db import models
from django.utils import timezone


class Reminder(models.Model):
    """User-scoped reminder item for the reminders page."""
    user = models.ForeignKey(
        'login.User',
        on_delete=models.CASCADE,
        related_name='reminders',
        db_index=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True, help_text="When the reminder is due")
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['is_completed', 'due_at', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_completed']),
            models.Index(fields=['user', 'due_at']),
        ]

    def __str__(self):
        base = f"{self.title}"
        if self.due_at:
            # Show in local time if USE_TZ is enabled
            due_disp = timezone.localtime(self.due_at) if timezone.is_aware(self.due_at) else self.due_at
            return f"{base} (due {due_disp:%Y-%m-%d %H:%M})"
        return base
