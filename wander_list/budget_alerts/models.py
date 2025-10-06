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
