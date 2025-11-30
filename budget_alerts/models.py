from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = settings.AUTH_USER_MODEL

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ba_categories")
    name = models.CharField(max_length=64)

    class Meta:
        unique_together = ("user", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name

class BudgetAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budget_alerts")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="alerts")
    amount_limit = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    threshold_percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        default=80
    )
    
    # Multi-threshold support
    threshold_50 = models.BooleanField(default=True, help_text="Alert at 50% usage")
    threshold_75 = models.BooleanField(default=True, help_text="Alert at 75% usage")
    threshold_90 = models.BooleanField(default=True, help_text="Alert at 90% usage")
    threshold_100 = models.BooleanField(default=True, help_text="Alert at 100% usage")
    
    # Snooze functionality
    snoozed_until = models.DateTimeField(null=True, blank=True, help_text="Snooze alerts until this time")
    
    notify_dashboard = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=False)
    notify_push = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.category} • ₱{self.amount_limit} • {self.threshold_percent}%"
    
    def is_snoozed(self):
        """Check if alert is currently snoozed."""
        from django.utils import timezone
        if self.snoozed_until and self.snoozed_until > timezone.now():
            return True
        return False
    
    def get_enabled_thresholds(self):
        """Return list of enabled threshold percentages."""
        thresholds = []
        if self.threshold_50:
            thresholds.append(50)
        if self.threshold_75:
            thresholds.append(75)
        if self.threshold_90:
            thresholds.append(90)
        if self.threshold_100:
            thresholds.append(100)
        return thresholds


class BudgetHistory(models.Model):
    """
    Tracks changes to budget alerts over time for historical analysis and trend tracking.
    """
    user_id = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=64, db_index=True)
    amount_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    threshold_percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(100)]
    )
    previous_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    change_reason = models.TextField(blank=True)
    change_date = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-change_date']
        indexes = [
            models.Index(fields=['-change_date', 'user_id']),
            models.Index(fields=['user_id', 'category']),
        ]
    
    def __str__(self):
        return f"{self.category} - ₱{self.amount_limit} ({self.change_date.strftime('%Y-%m-%d')})"
    
    def get_change_amount(self):
        """Calculate the change in budget limit."""
        if self.previous_limit:
            return self.amount_limit - self.previous_limit
        return Decimal('0.00')
    
    def get_change_percentage(self):
        """Calculate percentage change in budget limit."""
        if self.previous_limit and self.previous_limit > 0:
            change = ((self.amount_limit - self.previous_limit) / self.previous_limit) * 100
            return round(change, 2)
        return 0.0


class AlertHistory(models.Model):
    """
    Tracks when alerts are triggered for audit and snooze management.
    """
    SEVERITY_CHOICES = [
        ('info', 'Info (50%)'),
        ('warning', 'Warning (75%)'),
        ('danger', 'Danger (90%)'),
        ('critical', 'Critical (100%)'),
    ]
    
    alert = models.ForeignKey(BudgetAlert, on_delete=models.CASCADE, related_name='history')
    user_id = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=64)
    threshold_level = models.PositiveSmallIntegerField(
        help_text="The threshold percentage that was triggered (50, 75, 90, or 100)"
    )
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    current_spending = models.DecimalField(max_digits=12, decimal_places=2)
    budget_limit = models.DecimalField(max_digits=12, decimal_places=2)
    usage_percent = models.DecimalField(max_digits=5, decimal_places=2)
    triggered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['-triggered_at', 'user_id']),
            models.Index(fields=['user_id', 'category', 'threshold_level']),
        ]
    
    def __str__(self):
        return f"{self.category} - {self.threshold_level}% ({self.triggered_at.strftime('%Y-%m-%d %H:%M')})"
    
    def get_severity_badge_class(self):
        """Return Bootstrap badge class for severity."""
        severity_map = {
            'info': 'bg-info',
            'warning': 'bg-warning',
            'danger': 'bg-danger',
            'critical': 'bg-dark'
        }
        return severity_map.get(self.severity, 'bg-secondary')
    
    def get_severity_icon(self):
        """Return Font Awesome icon for severity."""
        icon_map = {
            'info': 'fa-info-circle',
            'warning': 'fa-exclamation-triangle',
            'danger': 'fa-exclamation-circle',
            'critical': 'fa-skull-crossbones'
        }
        return icon_map.get(self.severity, 'fa-bell')
