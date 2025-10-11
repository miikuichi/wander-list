from django.db import models
from django.conf import settings
from decimal import Decimal

User = settings.AUTH_USER_MODEL

# 1. CATEGORY MODEL (Required by Expense)
class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expense_categories")
    name = models.CharField(max_length=64)

    class Meta:
        unique_together = ("user", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name

# 2. EXPENSE MODEL
class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")

    # Attributes based on the "Log New Expense" form [image_c4f60f.png]:
    
    # 1. Expense Amount ($ 50.00)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # 2. Category (Select a category) - Links to the Category model
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="expenses")

    # 3. Expense Date (20/09/2025)
    date = models.DateField()

    # 4. Notes (Optional)
    notes = models.TextField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.category.name} - ${self.amount} on {self.date}"