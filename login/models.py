from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from decimal import Decimal

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Stores hashed password
    is_admin = models.BooleanField(default=False)
    daily_allowance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('500.00'),
        help_text="Daily spending limit in Philippine Pesos"
    )

    def __str__(self):
        return self.username
    
    def set_password(self, raw_password):
        """
        Hash and set the user's password.
        Use this instead of directly setting user.password.
        """
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """
        Check if the provided password matches the stored hash.
        Returns True if password is correct, False otherwise.
        """
        # Handle legacy plaintext passwords during migration
        if not self.password.startswith('pbkdf2_'):
            # This is a plaintext password - direct comparison for migration
            if self.password == raw_password:
                # Auto-upgrade to hashed password
                self.set_password(raw_password)
                self.save()
                return True
            return False
        
        # Standard hashed password check
        return check_password(raw_password, self.password)
    
    def get_daily_allowance_remaining(self):
        """
        Calculate remaining daily allowance for today.
        This would query Supabase expenses table in production.
        """
        # This is a placeholder - actual implementation would query Supabase
        return self.daily_allowance