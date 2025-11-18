from django.db import models
from django.utils import timezone


class NotificationLog(models.Model):
    """Track all notifications sent to users."""
    
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('dashboard', 'Dashboard Alert'),
    ]
    
    NOTIFICATION_CATEGORIES = [
        ('budget_alert', 'Budget Alert'),
        ('goal_milestone', 'Goal Milestone'),
        ('goal_deadline', 'Goal Deadline'),
        ('goal_achieved', 'Goal Achieved'),
        ('reminder', 'Reminder'),
        ('expense', 'Expense Alert'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]
    
    user_id = models.BigIntegerField(db_index=True, help_text="User ID from session")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    category = models.CharField(max_length=30, choices=NOTIFICATION_CATEGORIES)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional metadata
    related_object_type = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'savings_goal', 'budget_alert'
    related_object_id = models.BigIntegerField(blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        app_label = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', '-created_at']),
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['notification_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} - {self.title} ({self.status})"
    
    def mark_sent(self):
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_failed(self, error):
        """Mark notification as failed with error message."""
        self.status = 'failed'
        self.error_message = str(error)
        self.save()
    
    def mark_read(self):
        """Mark notification as read."""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()


class UserNotificationPreference(models.Model):
    """Store user preferences for different notification types."""
    
    user_id = models.BigIntegerField(unique=True, db_index=True)
    
    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_budget_alerts = models.BooleanField(default=True)
    email_goal_milestones = models.BooleanField(default=True)
    email_goal_deadlines = models.BooleanField(default=True)
    email_reminders = models.BooleanField(default=True)
    
    # Push notification preferences
    push_enabled = models.BooleanField(default=False)
    push_budget_alerts = models.BooleanField(default=True)
    push_goal_milestones = models.BooleanField(default=True)
    push_goal_deadlines = models.BooleanField(default=True)
    push_reminders = models.BooleanField(default=True)
    
    # FCM token for push notifications
    fcm_token = models.TextField(blank=True, null=True, help_text="Firebase Cloud Messaging token")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'notifications'
    
    def __str__(self):
        return f"Preferences for User {self.user_id}"


class GoalAlert(models.Model):
    """Track savings goal alerts and milestones."""
    
    ALERT_TYPES = [
        ('milestone_25', '25% Progress'),
        ('milestone_50', '50% Progress'),
        ('milestone_75', '75% Progress'),
        ('milestone_100', 'Goal Achieved'),
        ('deadline_week', '1 Week to Deadline'),
        ('deadline_day', '1 Day to Deadline'),
        ('deadline_passed', 'Deadline Passed'),
    ]
    
    goal_id = models.BigIntegerField(db_index=True)
    user_id = models.BigIntegerField(db_index=True)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    
    # Track if alert was triggered
    triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(blank=True, null=True)
    
    # Link to notification logs
    notification_logs = models.ManyToManyField(NotificationLog, blank=True, related_name='goal_alerts')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'notifications'
        ordering = ['-created_at']
        unique_together = ['goal_id', 'alert_type']
        indexes = [
            models.Index(fields=['goal_id', 'triggered']),
            models.Index(fields=['user_id', '-created_at']),
        ]
    
    def __str__(self):
        return f"Goal {self.goal_id} - {self.get_alert_type_display()}"
    
    def trigger(self):
        """Mark alert as triggered."""
        if not self.triggered:
            self.triggered = True
            self.triggered_at = timezone.now()
            self.save()
