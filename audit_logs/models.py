from django.db import models
import json


class AuditLog(models.Model):
    """
    Model to track all user actions and system events for security and compliance.
    """
    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('ACCESS_DENIED', 'Access Denied'),
        ('BUDGET_BREACH', 'Budget Threshold Breach'),
        ('ALERT_TRIGGERED', 'Alert Triggered'),
    ]
    
    RESOURCE_TYPES = [
        ('expense', 'Expense'),
        ('goal', 'Savings Goal'),
        ('alert', 'Budget Alert'),
        ('reminder', 'Reminder'),
        ('user', 'User'),
        ('monthly_allowance', 'Monthly Allowance'),
        ('system', 'System'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, db_index=True)
    resource_type = models.CharField(max_length=50, choices=RESOURCE_TYPES, db_index=True)
    resource_id = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'user_id']),
            models.Index(fields=['action_type', 'resource_type']),
        ]
    
    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.user_id} - {self.action_type} {self.resource_type}"
    
    def get_metadata_display(self):
        """Return formatted metadata for display."""
        if not self.metadata:
            return "No metadata"
        return json.dumps(self.metadata, indent=2)
