from django.db import models
from decimal import Decimal

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    is_admin = models.BooleanField(default=False)
    daily_allowance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('500.00'),
        help_text="Daily spending limit in Philippine Pesos"
    )

    def __str__(self):
        return self.username
    
    def get_daily_allowance_remaining(self):
        """
        Calculate remaining daily allowance for today.
        This would query Supabase expenses table in production.
        """
        # This is a placeholder - actual implementation would query Supabase
        return self.daily_allowance